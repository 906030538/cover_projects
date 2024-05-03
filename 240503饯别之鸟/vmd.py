#!python
from io import BufferedReader, BufferedWriter
import sys
import struct
import numpy

def quaternion_to_euler(quat: [float, float, float, float]) -> [float,float,float]:
    z, x, y, w = quat
    # pitch (y-axis rotation)
    sinr_cosp = 2 * ((w * y) + (x * z))
    cosr_cosp = 1 - (2 * ((x ** 2) + (y ** 2)))
    pitch = -numpy.arctan2(sinr_cosp, cosr_cosp)
    # yaw (z-axis rotation)
    siny_cosp = 2 * ((-w * z) - (x * y))
    cosy_cosp = 1 - (2 * ((x ** 2) + (z ** 2)))
    yaw = numpy.arctan2(siny_cosp, cosy_cosp)
    # roll (x-axis rotation)
    sinp = 2 * ((z * y) - (w * x))
    if sinp >= 1.0:
        roll = -numpy.pi / 2  # use 90 degrees if out of range
    elif sinp <= -1.0:
        roll = numpy.pi / 2
    else:
        roll = -numpy.arcsin(sinp)
    # fixing the x rotation, part 1
    if x ** 2 > 0.5 or w < 0:
        if x < 0:
            roll = -numpy.pi - roll
        else:
            roll = numpy.pi * numpy.copysign(1, w) - roll
    # fixing the x rotation, part 2
    if roll > (numpy.pi / 2):
        roll = numpy.pi - roll
    elif roll < -(numpy.pi / 2):
        roll = -numpy.pi - roll
    roll = numpy.degrees(roll)
    pitch = numpy.degrees(pitch)
    yaw = numpy.degrees(yaw)
    return -yaw, roll, -pitch

class Frame2:
    name = ""
    num = 0
    # x, y, z
    pos = (0.0, 0.0, 0.0)
    # x, y, z, w
    rot = (0.0, 0.0, 0.0, 0.0)
    interp = "\x7f" * 64
    
    def read_frame(f: BufferedReader):
        frame = Frame2()
        frame.name = f.read(15).decode("shift-jis")
        frame.num = struct.unpack("I", f.read(4))[0]
        pos_x = struct.unpack("f", f.read(4))[0]
        pos_y = struct.unpack("f", f.read(4))[0]
        pos_z = struct.unpack("f", f.read(4))[0]
        frame.pos = (pos_x, pos_y, pos_z)
        rot_x = struct.unpack("f", f.read(4))[0]
        rot_y = struct.unpack("f", f.read(4))[0]
        rot_z = struct.unpack("f", f.read(4))[0]
        rot_w = struct.unpack("f", f.read(4))[0]
        frame.rot = (rot_x, rot_y, rot_z, rot_w)
        frame.interp = f.read(64)
        return frame
    
    def dump(this, f: BufferedWriter):
        f.write(this.name.encode("shift-jis"))
        f.write(struct.pack("I", this.num))
        for i in this.pos:
            f.write(struct.pack("f", i))
        for i in this.rot:
            f.write(struct.pack("f", i))
        f.write(this.interp)
        return

class FaceFrame2:
    name = ""
    num = 0
    weight = 0.0
    
    def read_frame(f: BufferedReader):
        frame = FaceFrame2()
        frame.name = f.read(15).decode("shift-jis")
        frame.num = struct.unpack("I", f.read(4))[0]
        frame.weight = struct.unpack("f", f.read(4))[0]
        return frame
    
    def dump(this, f: BufferedWriter):
        f.write(this.name.encode("shift-jis"))
        f.write(struct.pack("I", this.num))
        f.write(struct.pack("f", this.weight))
        return

class CameraFrame2:
    num = 0
    distance = 0.0
    # x, y, z
    pos = (0.0, 0.0, 0.0)
    # x, y, z
    rot = (0.0, 0.0, 0.0)
    interp = b"\x00" * 24
    fov = 0
    perspective = 0
    
    def read_frame(f: BufferedReader):
        frame = CameraFrame2()
        frame.num = struct.unpack("I", f.read(4))[0]
        distance = struct.unpack("f", f.read(4))[0]
        pos_x = struct.unpack("f", f.read(4))[0]
        pos_y = struct.unpack("f", f.read(4))[0]
        pos_z = struct.unpack("f", f.read(4))[0]
        frame.pos = (pos_x, pos_y, pos_z)
        rot_x = struct.unpack("f", f.read(4))[0]
        rot_y = struct.unpack("f", f.read(4))[0]
        rot_z = struct.unpack("f", f.read(4))[0]
        frame.rot = (rot_x, rot_y, rot_z)
        frame.interp = f.read(24)
        frame.fov = struct.unpack("I", f.read(4))[0]
        frame.perspective = struct.unpack("B", f.read(1))[0]
        return frame
    
    def dump(this, f: BufferedWriter):
        f.write(struct.pack("I", this.num))
        f.write(struct.pack("f", this.distance))
        for i in this.pos:
            f.write(struct.pack("f", i))
        for i in this.rot:
            f.write(struct.pack("f", i))
        f.write(this.interp)
        f.write(struct.pack("I", this.fov))
        f.write(struct.pack("B", this.perspective))
        return

class VMD2:
    magic = "Vocaloid Motion Data 0002\0\0\0\0\0"
    model = "MODEL_00"
    frames = 0
    frame = []
    face_frames = 0
    face_frame = []
    camera_frames = 0
    camera_frame = []

    def read_vmd(f: BufferedReader):
        if f.read(30).decode("shift-jis") != VMD2.magic:
            print("Failed to parse VMD header", file=sys.stderr)
            return None
        vmd = VMD2()
        vmd.model = f.read(20).decode("shift-jis")
        
        vmd.frames = struct.unpack("I", f.read(4))[0]
        for i in range(vmd.frames):
            frame = Frame2.read_frame(f)
            vmd.frame.append(frame)
        
        vmd.face_frames = struct.unpack("I", f.read(4))[0]
        for i in range(vmd.face_frames):
            frame = FaceFrame2.read_frame(f)
            vmd.face_frame.append(frame)
        
        vmd.camera_frames = struct.unpack("I", f.read(4))[0]
        for i in range(vmd.camera_frames):
            frame = CameraFrame2.read_frame(f)
            vmd.camera_frame.append(frame)
        return vmd
    
    def dump(this, f: BufferedWriter):
        f.write(this.magic.encode("shift-jis"))
        f.write(this.model.encode("shift-jis"))
        f.write(struct.pack("I", len(this.frame)))
        for frame in this.frame:
            frame.dump(f)
        f.write(struct.pack("I", len(this.face_frame)))
        for frame in this.face_frame:
            frame.dump(f)
        f.write(struct.pack("I", len(this.camera_frame)))
        for frame in this.camera_frame:
            frame.dump(f)
        f.write(struct.pack("I", 0))
        f.write(struct.pack("I", 0))
        return

if __name__ == "__main__":
    arg1 = "test_mo1.vmd"
    arg2 = "test_mo1_1.vmd"
    with open(arg1, "rb") as f:
        vmd = VMD2.read_vmd(f)
        tail = f.read()

    vmd.frame = [frame for frame in vmd.frame if frame.name.strip('\0') != "ATAMA"]

    for frame in vmd.frame:
        name = frame.name.strip('\0')
#         if name == "左腕":
#             x, y, z, w = frame.rot
#             frame.rot = (x, y, z + numpy.pi / 12, w)
#         if name == "左ひじ":
#             x, y, z, w = frame.rot
#             frame.rot = (x, y, z, w - numpy.pi / 12)
        if name == "右肩" or name == "左肩":
            x, y, z, w = frame.rot
            frame.rot = (x, y, z/2, w)
#         if name == "右腕":
#             x, y, z, w = frame.rot
#             frame.rot = (x, y, z - numpy.pi / 12, w)
    tmp = None
    for frame in vmd.frame[::-1]:
        name = frame.name.strip('\0')
        if name == "グルーブ":
            tmp = frame
        if name == "センター":
            frame.pos = (frame.pos[0] + tmp.pos[0], frame.pos[1] + tmp.pos[1], frame.pos[2] + tmp.pos[2])
            frame.rot = tmp.rot

    with open(arg2, "wb") as f:
        vmd.dump(f)