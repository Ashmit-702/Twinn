from dataclasses import dataclass

CHANNELS = [
    "temperature", "pressure", "vibration", "cpu_load",
    "net_in_pps", "net_out_pps", "failed_logins", "cmd_rate",
]
_LOGIN = (0.05, 0.22)  # failed logins per sample: ~Poisson(0.05)


@dataclass(frozen=True)
class Profile:
    key: str
    prefix: str
    label: str
    criticality: float  # 0..1, used by risk assessment
    baselines: dict  # channel -> (mean, std) of normal operation


PROFILES: dict[str, Profile] = {
    "cnc": Profile("cnc", "CNC-MA", "CNC Machine", 0.9, {
        "temperature": (62, 2.0), "pressure": (6.0, 0.15), "vibration": (2.2, 0.25), "cpu_load": (35, 5),
        "net_in_pps": (120, 15), "net_out_pps": (90, 12), "failed_logins": _LOGIN, "cmd_rate": (40, 5)}),
    "robot": Profile("robot", "ROBOT-AR", "Robotic Arm", 0.8, {
        "temperature": (55, 1.8), "pressure": (5.0, 0.12), "vibration": (1.5, 0.2), "cpu_load": (40, 5),
        "net_in_pps": (150, 18), "net_out_pps": (130, 15), "failed_logins": _LOGIN, "cmd_rate": (60, 6)}),
    "plc": Profile("plc", "PLC-IC", "Industrial Controller", 1.0, {
        "temperature": (45, 1.2), "pressure": (0.8, 0.05), "vibration": (0.2, 0.03), "cpu_load": (30, 4),
        "net_in_pps": (300, 30), "net_out_pps": (280, 28), "failed_logins": _LOGIN, "cmd_rate": (120, 10)}),
    "temp_sensor": Profile("temp_sensor", "TEMP-SN", "Temperature Sensor", 0.5, {
        "temperature": (38, 0.8), "pressure": (1.0, 0.03), "vibration": (0.05, 0.01), "cpu_load": (8, 1.5),
        "net_in_pps": (20, 3), "net_out_pps": (25, 3), "failed_logins": _LOGIN, "cmd_rate": (2, 0.5)}),
    "pressure_sensor": Profile("pressure_sensor", "PRES-SN", "Pressure Sensor", 0.5, {
        "temperature": (30, 0.7), "pressure": (7.5, 0.1), "vibration": (0.05, 0.01), "cpu_load": (8, 1.5),
        "net_in_pps": (20, 3), "net_out_pps": (25, 3), "failed_logins": _LOGIN, "cmd_rate": (2, 0.5)}),
}
FLEET_MIX = [("cnc", 0.30), ("robot", 0.25), ("plc", 0.15), ("temp_sensor", 0.15), ("pressure_sensor", 0.15)]
