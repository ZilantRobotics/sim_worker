import dataclasses

from autopilot_tools.mission_file.mission_result import MissionResult, StatusCode as StatusCode2

from src.api.core import Result, StatusCode

r = MissionResult(
    status=StatusCode2.OK
)
f = StatusCode2.OK
res = Result(
    status=StatusCode.in_progress,
    message={'res': dataclasses.asdict(r)}
)
r_p = res.pack()
