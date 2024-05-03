#!python
import sys
import json
import numpy
import struct
import vmd

MLTDFrameRate = 60
ScaleUnityToVmd = 12.5

def bezier(p1: float, cp: float, p2: float, t: float) -> float:
    tt = 1 - t
    return tt * tt * p1 + 2 * t * tt * cp + t * t * p2

def bezier2(p1: float, cp1: float, cp2: float, p2: float, t: float) -> float:
    tt = 1 - t
    return (tt ** 3) * p1 + 3 * (tt ** 2) * t * cp1 + 3 * tt * (t ** 2) * cp2 + (t ** 3)* p2

def compute_fcurve_naive(cur_value: float, next_value: float, tan1: float, tan2: float, dt: float, t: float) -> float:
    match (cur_value + tan1 / 3 * dt, tan2 / 3 * dt - next_value):
        case (numpy.inf, numpy.inf):
            return cur_value + t * (next_value - cur_value)
        case (numpy.inf, cp2):
            return bezier(cur_value, -cp2, next_value, t)
        case (cp1, numpy.inf):
            return bezier(cur_value, cp1, next_value, t)
        case (cp1, cp2):
            return bezier2(cur_value, cp1, -cp2, next_value, t)

def get_interpolated_value(curve: list[float], time: float) -> float:
    for i in range(len(curve) // 4 - 1):
        cur_time, cur_value, tan1, tan2, next_time, next_value = curve[i*4:i*4+6]
        if time > next_time:
            continue
        dt = next_time - cur_time
        t = (time - cur_time) / dt
        # TODO: use F-curve interpolation
        return compute_fcurve_naive(cur_value, next_value, tan1, tan2, dt, t)
    return curve[len(curve) - 3]

def get_lower_clamped_value(curve: list[float], time: float) -> float:
    for i in range(len(curve) // 4 - 1):
        next_time = curve[(i+1)*4]
        if time > next_time:
            continue
        cur_value = curve[i*4 + 1]
        return cur_value
    return curve[len(curve) - 3]

class CameraFrame:
    num = 0
    time = 0.0
    focal_length = 0.0
    cut = 0
    angle = (0.0, 0.0, 0.0)
    position = (0.0, 0.0, 0.0)
    target = (0.0, 0.0, 0.0)

def character_imas_motion_asset(camera_motion: dict) -> list[CameraFrame]:
    curves = [[0.0, 0.0, 0.0, 0.0]] * 11
    for curve in camera_motion["curves"]:
        c = [numpy.inf if f == "Infinity" else f for f in curve["values"]]
        if curve["path"] == "CamBase":
            if "property_name focalLength" in curve["attribs"]:
                curves[0] = c
            elif "property_name camCut" in curve["attribs"]:
                curves[1] = c
        if curve["path"] == "CamBaseS":
            if "property_type AngleX" in curve["attribs"]:
                curves[2] = c
            elif "property_type AngleY" in curve["attribs"]:
                curves[3] = c
            elif "property_type AngleZ" in curve["attribs"]:
                curves[4] = c
            elif "property_type PositionX" in curve["attribs"]:
                curves[5] = c
            elif "property_type PositionY" in curve["attribs"]:
                curves[6] = c
            elif "property_type PositionZ" in curve["attribs"]:
                curves[7] = c
        if curve["path"] == "CamTgtS":
            if "property_type PositionX" in curve["attribs"]:
                curves[8] = c
            elif "property_type PositionY" in curve["attribs"]:
                curves[9] = c
            elif "property_type PositionZ" in curve["attribs"]:
                curves[10] = c

    duration = max(map(lambda c: max(c[::4]), curves))
    count = int(duration * 60)
    
    frames = []
    for i in range(count):
        frame = CameraFrame()
        frame.num = i
        time = i / 60
        frame.time = time
        frame.focal_length = get_interpolated_value(curves[0], time)
        frame.cut = int(get_lower_clamped_value(curves[1], time))
        frame.angle = (
            get_interpolated_value(curves[2], time),
            get_interpolated_value(curves[3], time),
            get_interpolated_value(curves[4], time),
        )
        frame.position = (
            get_interpolated_value(curves[5], time),
            get_interpolated_value(curves[6], time),
            get_interpolated_value(curves[7], time),
        )
        frame.target = (
            get_interpolated_value(curves[8], time),
            get_interpolated_value(curves[9], time),
            get_interpolated_value(curves[10], time),
        )
        # print("%7.3f %7.3f %3d" % (frame.time, frame.focal_length, frame.cut), end=" ")
        # print("[%7.3f,%7.3f,%7.3f]" % frame.angle, end=" ")
        # print("[%7.3f,%7.3f,%7.3f]" % frame.position, end=" ")
        # print("[%7.3f,%7.3f,%7.3f]" % frame.target, end=" ")
        # print()
        frames.append(frame)
    
    return frames

def quaternion_look_at(forward: numpy.ndarray) -> tuple[float, float, float, float]:
    axis = numpy.cross(forward, numpy.array([0, 0, 1]))
    norm = numpy.linalg.norm(axis)
    axis = numpy.array([0, 1, 0]) if norm == 0 else (axis / norm)
    angle = numpy.arccos(forward[2])
    angle = angle / 2
    axis = axis * numpy.sin(angle)
    qw = numpy.cos(angle)
    return [axis[0], axis[1], axis[2], qw]

def quaternion_to_euler(q):
    y, x, z, w = q
    r1 = w**2 - y**2
    r2 = x**2 - z**2
    pitch = numpy.arctan2(2 * (y * x + w * z), r1 + r2)
    roll  = numpy.arcsin(-2 * (x * z - w * y))
    yaw   = numpy.arctan2(2 * (y * z + w * x), r1 - r2)
    return roll, pitch, yaw

def compute_mmd_orientation(q, az):
    roll, yaw, pitch = quaternion_to_euler(q)
    # roll = -roll
    # pitch += numpy.pi
    # Unity is left handed, MMD is right handed
    yaw = -numpy.radians(az)
    return roll, pitch, yaw

class MvdCameraFrame:
    num = 0
    position = [0.0, 0.0, 0.0]
    distance = 0.0
    rotation = [0.0, 0.0, 0.0]
    fov = 0.0
    is_spline = False
    translation_interpolation = [0, 0, 255, 255]
    rotation_interpolation = [0, 0, 255, 255]
    distance_interpolation = [0, 0, 255, 255]
    fov_interpolation = [0, 0, 255, 255]

    def to_vmd(self):
        frame = vmd.CameraFrame2()
        frame.num = self.num
        frame.distance = self.distance / 10
        frame.pos = self.position
        frame.rot = self.rotation + numpy.array([numpy.pi, 0, numpy.pi])
        frame.fov = 20
        return frame

    def dump(self, f):
        f.write(struct.pack("Q", self.num))
        f.write(struct.pack("f", self.distance))
        for i in self.position:
            f.write(struct.pack("f", i))
        for i in self.rotation:
            f.write(struct.pack("f", i))
        f.write(struct.pack("f", self.fov))
        f.write(struct.pack("B", self.is_spline))
        f.write(b"\0\0\0")
        for i in self.translation_interpolation:
            f.write(struct.pack("B", i))
        for i in self.rotation_interpolation:
            f.write(struct.pack("B", i))
        for i in self.distance_interpolation:
            f.write(struct.pack("B", i))
        for i in self.fov_interpolation:
            f.write(struct.pack("B", i))

class MvdMotion:
    magic = "Motion Vector Data file\0\0\0\0\0\0\0"
    name = "カメラ00"
    fps = 30
    frames = []
    fov = 0.0
    
    def dump(self, f):
        f.write(self.magic.encode())
        f.write(struct.pack("f", 1.0))
        f.write(struct.pack("B", 1))
        # WriteCameraMotion
        b_name = self.name.encode()
        f.write(struct.pack("I", len(b_name)))
        f.write(b_name)
        f.write(struct.pack("I", len(b_name)))
        f.write(b_name)
        f.write(struct.pack("f", self.fps))
        f.write(struct.pack("I", 0))
        f.write(struct.pack("B", False))
        f.write(struct.pack("B", False))
        f.write(struct.pack("I", 0))
        f.write(struct.pack("I", 0))
        f.write(struct.pack("Q", 1))
        # WriteNameList
        f.write(struct.pack("I", 0))
        f.write(struct.pack("I", len(b_name)))
        f.write(b_name)
        # WriteCamera
        f.write(struct.pack("B", 96))
        f.write(struct.pack("B", 3))
        f.write(struct.pack("I", 0))
        f.write(struct.pack("I", 64))
        f.write(struct.pack("I", len(self.frames)))
        f.write(struct.pack("I", 4))
        f.write(struct.pack("I", 1))
        for index, frame in enumerate(self.frames):
            f.write(struct.pack("I", 0))
            frame.dump(f)
        # WriteCameraProperty
        f.write(struct.pack("B", 104))
        f.write(struct.pack("B", 2))
        f.write(struct.pack("I", 1))
        f.write(struct.pack("I", 32))
        f.write(struct.pack("I", 1))
        f.write(struct.pack("Q", 0))
        # PropertyFrames
        f.write(struct.pack("I", 0))
        # f.Enabled = true;
        f.write(struct.pack("B", True))
        # f.IsPerspective = true;
        f.write(struct.pack("B", True))
        # f.Alpha = 1;
        f.write(struct.pack("f", 1.0))
        # f.EffectEnabled = true;
        f.write(struct.pack("B", True))
        # f.DynamicFovEnabled = false;
        f.write(struct.pack("B", False))
        # f.DynamicFovRate = 0.1f;
        f.write(struct.pack("f", 0.1))
        # f.DynamicFovCoefficient = 1;
        f.write(struct.pack("f", 1.0))
        # f.RelatedBoneId = -1;
        f.write(struct.pack("i", -1))
        # f.RelatedModelId = -1;
        f.write(struct.pack("i", -1))
        # Write EOF
        f.write(b"\xff\0")

def create_mvd_frames(frame: CameraFrame) -> MvdCameraFrame:
    mvd_frame = MvdCameraFrame()
    mvd_frame.num = frame.num
    mvd_frame.position = numpy.asarray([-frame.position[0], frame.position[1], -frame.position[2]]) * ScaleUnityToVmd
    target = numpy.asarray([-frame.target[0], frame.target[1], -frame.target[2]]) * ScaleUnityToVmd
    distance = target - mvd_frame.position
    # should not be zero
    mvd_frame.distance = numpy.linalg.norm(distance)
    q = quaternion_look_at(distance / mvd_frame.distance)
    mvd_frame.rotation = compute_mmd_orientation(q, frame.angle[2])
    mvd_frame.rotation = (mvd_frame.rotation[0] + numpy.pi, mvd_frame.rotation[1], mvd_frame.rotation[2] + numpy.pi)
    mvd_frame.fov = 2 * numpy.arctan(11 / frame.focal_length)
    return mvd_frame

def create_vmd_frames(frame: CameraFrame) -> vmd.CameraFrame2:
    vmd_frame = vmd.CameraFrame2()
    vmd_frame.num = frame.num
    vmd_frame.pos = numpy.asarray([-frame.position[0], frame.position[1], -frame.position[2]]) * ScaleUnityToVmd
    target = numpy.asarray([-frame.target[0], frame.target[1], -frame.target[2]]) * ScaleUnityToVmd
    distance = target - vmd_frame.pos
    # should not be zero
    norm = numpy.linalg.norm(distance)
    q = quaternion_look_at(distance / norm)
    vmd_frame.distance = norm / 10
    vmd_frame.rot = compute_mmd_orientation(q, frame.angle[2])
    vmd_frame.fov = 20
    # vmd_frame.fov = int(numpy.degrees(2 * numpy.arctan(11 / frame.focal_length)))
    return vmd_frame

file = "cam_hanamk_01_cam.imo.json"
with open(file) as f:
    imo = json.load(f)

frames = character_imas_motion_asset(imo)

out = MvdMotion()
out.frames = [create_mvd_frames(frame) for frame in frames]
# out = vmd.VMD2()
# out.model = "カメラ・照明\0\0\0\0\0\0\0\0"
# out.camera_frame = [create_vmd_frames(frame) for frame in frames]

for frame in out.frames:
    if frame.num > 2219 and frame.num < 2398:
        frame.distance -= 5
    elif frame.num > 3517 and frame.num < 3594:
        frame.distance -= 62
    elif frame.num > 4463 and frame.num < 4505:
        frame.distance -= 24
    elif frame.num > 5601 and frame.num < 5647:
        frame.distance -= 46

outfile = "test_cam1.mvd"
with open(outfile, "wb") as f:
    out.dump(f)