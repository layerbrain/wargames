local wargames_json = json
if wargames_json == nil then
	wargames_json = (loadfile "external/script/json.lua")()
end

local wargames_last_tick = -1

local function safe(default, fn)
	local ok, value = pcall(fn)
	if ok then
		return value
	end
	return default
end

local function player_state(slot)
	local old_id = safe(-1, function() return id() end)
	local exists = safe(false, function() return player(slot) end)
	local row = {slot = slot, exists = exists}
	if exists then
		row.name = safe("", function() return name() end)
		row.life = safe(0, function() return life() end)
		row.life_max = safe(0, function() return lifemax() end)
		row.power = safe(0, function() return power() end)
		row.power_max = safe(0, function() return powermax() end)
		row.x = safe(nil, function() return posX() end)
		row.y = safe(nil, function() return posY() end)
		row.vx = safe(nil, function() return velX() end)
		row.vy = safe(nil, function() return velY() end)
		row.state_no = safe(0, function() return stateno() end)
		row.move_type = safe("", function() return movetype() end)
		row.control = safe(false, function() return ctrl() end)
		row.alive = safe(false, function() return alive() end)
		row.ai_level = safe(0, function() return ailevel() end)
		row.hit_count = safe(0, function() return hitcount() end)
	else
		row.name = ""
		row.life = 0
		row.life_max = 0
		row.power = 0
		row.power_max = 0
		row.x = nil
		row.y = nil
		row.vx = nil
		row.vy = nil
		row.state_no = 0
		row.move_type = ""
		row.control = false
		row.alive = false
		row.ai_level = 0
		row.hit_count = 0
	end
	if old_id ~= -1 then
		pcall(function() playerid(old_id) end)
	end
	return row
end

function wargames_state_export()
	local path = os.getenv("WARGAMES_IKEMEN_STATE_PATH")
	if path == nil or path == "" then
		return
	end
	local interval = tonumber(os.getenv("WARGAMES_IKEMEN_STATE_INTERVAL_TICKS") or "1") or 1
	local tick = safe(0, function() return gametime() end)
	if tick == wargames_last_tick or tick % interval ~= 0 then
		return
	end
	wargames_last_tick = tick

	local winner = safe(-1, function() return winnerteam() end)
	local over = safe(false, function() return matchover() end)
	local row = {
		tick = tick,
		match = {
			round_state = safe(0, function() return roundstate() end),
			round_no = safe(0, function() return roundno() end),
			fight_time = safe(0, function() return fighttime() end),
			match_over = over,
			winner_team = winner,
		},
		players = {
			player_state(1),
			player_state(2),
		},
	}
	row.mission = {
		finished = over and winner == 1,
		failed = over and winner ~= 1 and winner ~= -1,
	}

	local file = io.open(path, "a")
	if file ~= nil then
		file:write(wargames_json.encode(row), "\n")
		file:close()
	end
end
