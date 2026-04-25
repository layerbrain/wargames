using System;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Text;
using OpenRA;
using OpenRA.Traits;

namespace OpenRA.Mods.Common.Traits
{
    [TraitLocation(SystemActors.World)]
    public sealed class WarGamesStateExportInfo : TraitInfo
    {
        public override object Create(ActorInitializer init) => new WarGamesStateExport();
    }

    public sealed class WarGamesStateExport : ITick, IDisposable
    {
        readonly Socket socket;
        readonly Stream stream;

        public WarGamesStateExport()
        {
            var path = Environment.GetEnvironmentVariable("PROBE_SOCK");
            if (string.IsNullOrEmpty(path))
                return;

            socket = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
            socket.Connect(new UnixDomainSocketEndPoint(path));
            stream = new NetworkStream(socket, ownsSocket: true);
        }

        public void Tick(Actor self)
        {
            if (stream == null)
                return;

            var world = self.World;
            var fields = new Dictionary<string, object>
            {
                ["v"] = 1,
                ["tick"] = world.WorldTick,
                ["us"] = new Dictionary<string, object> { ["id"] = "p1", ["cash"] = 0 },
                ["enemy"] = new Dictionary<string, object> { ["id"] = "p2", ["cash"] = 0 },
                ["units"] = Array.Empty<object>(),
                ["buildings"] = Array.Empty<object>(),
                ["resources"] = Array.Empty<object>(),
                ["mission"] = new Dictionary<string, object>
                {
                    ["elapsed_ticks"] = world.WorldTick,
                    ["objectives"] = Array.Empty<object>(),
                    ["finished"] = false,
                    ["failed"] = false,
                },
            };

            var payload = MessagePackEncode(fields);
            Span<byte> prefix = stackalloc byte[4];
            BinaryPrimitives.WriteUInt32BigEndian(prefix, (uint)payload.Length);
            stream.Write(prefix);
            stream.Write(payload, 0, payload.Length);
            stream.Flush();
        }

        public void Dispose()
        {
            stream?.Dispose();
            socket?.Dispose();
        }

        static byte[] MessagePackEncode(object value)
        {
            using var ms = new MemoryStream();
            WriteValue(ms, value);
            return ms.ToArray();
        }

        static void WriteValue(Stream stream, object value)
        {
            switch (value)
            {
                case null:
                    stream.WriteByte(0xc0);
                    return;
                case bool b:
                    stream.WriteByte(b ? (byte)0xc3 : (byte)0xc2);
                    return;
                case int i:
                    WriteInteger(stream, i);
                    return;
                case uint u:
                    WriteUnsigned(stream, u);
                    return;
                case string s:
                    WriteString(stream, s);
                    return;
                case Dictionary<string, object> map:
                    WriteMap(stream, map);
                    return;
                case object[] array:
                    WriteArray(stream, array);
                    return;
                default:
                    throw new InvalidOperationException($"Unsupported MessagePack value: {value.GetType()}");
            }
        }

        static void WriteInteger(Stream stream, int value)
        {
            if (value >= 0)
            {
                WriteUnsigned(stream, (uint)value);
                return;
            }

            if (value >= sbyte.MinValue)
            {
                stream.WriteByte(0xd0);
                stream.WriteByte((byte)(sbyte)value);
                return;
            }

            stream.WriteByte(0xd2);
            Span<byte> bytes = stackalloc byte[4];
            BinaryPrimitives.WriteInt32BigEndian(bytes, value);
            stream.Write(bytes);
        }

        static void WriteUnsigned(Stream stream, uint value)
        {
            if (value <= 0x7f)
            {
                stream.WriteByte((byte)value);
                return;
            }

            if (value <= byte.MaxValue)
            {
                stream.WriteByte(0xcc);
                stream.WriteByte((byte)value);
                return;
            }

            if (value <= ushort.MaxValue)
            {
                stream.WriteByte(0xcd);
                Span<byte> bytes = stackalloc byte[2];
                BinaryPrimitives.WriteUInt16BigEndian(bytes, (ushort)value);
                stream.Write(bytes);
                return;
            }

            stream.WriteByte(0xce);
            Span<byte> data = stackalloc byte[4];
            BinaryPrimitives.WriteUInt32BigEndian(data, value);
            stream.Write(data);
        }

        static void WriteString(Stream stream, string value)
        {
            var bytes = Encoding.UTF8.GetBytes(value);
            if (bytes.Length <= 31)
                stream.WriteByte((byte)(0xa0 | bytes.Length));
            else if (bytes.Length <= byte.MaxValue)
            {
                stream.WriteByte(0xd9);
                stream.WriteByte((byte)bytes.Length);
            }
            else if (bytes.Length <= ushort.MaxValue)
            {
                stream.WriteByte(0xda);
                Span<byte> length = stackalloc byte[2];
                BinaryPrimitives.WriteUInt16BigEndian(length, (ushort)bytes.Length);
                stream.Write(length);
            }
            else
                throw new InvalidOperationException("String is too long for the WarGames probe frame");

            stream.Write(bytes, 0, bytes.Length);
        }

        static void WriteMap(Stream stream, Dictionary<string, object> map)
        {
            if (map.Count > 15)
                throw new InvalidOperationException("Probe maps support up to 15 keys");
            stream.WriteByte((byte)(0x80 | map.Count));
            foreach (var kv in map)
            {
                WriteString(stream, kv.Key);
                WriteValue(stream, kv.Value);
            }
        }

        static void WriteArray(Stream stream, object[] array)
        {
            if (array.Length > 15)
                throw new InvalidOperationException("Probe arrays support up to 15 entries");
            stream.WriteByte((byte)(0x90 | array.Length));
            foreach (var item in array)
                WriteValue(stream, item);
        }
    }
}
