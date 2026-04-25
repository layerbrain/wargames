from __future__ import annotations

from openreward.environments import Server

from wargames_openreward.env_redalert import OPENREWARD_ENVIRONMENTS

app = Server(list(OPENREWARD_ENVIRONMENTS), return_errors="exception").app


def main() -> None:
    Server(list(OPENREWARD_ENVIRONMENTS), return_errors="exception").run()


if __name__ == "__main__":
    main()
