import numpy as np
from struct import unpack

ML_TWOSIDED = 4
NO_SIDEDEF = 0xffff


def null_pad(string, length=8):
    return string + chr(0) * (length - len(string))


MAP_LUMPS = ['THINGS', 'LINEDEFS', 'SIDEDEFS', 'VERTEXES', 'SEGS', 'SSECTORS', 'NODES', 'SECTORS', 'REJECT', 'BLOCKMAP']
MAP_LUMPS = [null_pad(n) for n in MAP_LUMPS]


# reject lump --> 2d bool array
def read_reject(fn):
    with open(fn,'rb') as f:
        fr = f.read()
    n_sectors = int(np.ceil(np.sqrt(8.0*len(fr)-7.0)))
    bits = np.unpackbits(np.frombuffer(fr, dtype='B'), bitorder='little')
    return bits[:n_sectors*n_sectors].reshape((n_sectors,n_sectors)).astype('bool')


# 2d bool array --> reject lump
def write_reject(reject, fn):
    with open(fn,'wb') as f:
        f.write(np.packbits(reject.reshape(-1).astype('B'), bitorder='little').tobytes())


def get_map_lmps(in_wad, which_map):
    which_map = null_pad(which_map)
    wad_data = []
    lmp_list = []
    with open(in_wad,'rb') as f:
        f.read(4) # PWAD
        (n_lmp, p_dir) = unpack('ii', f.read(8))
        f.seek(p_dir)
        for i in range(n_lmp):
            (lmp_pos, lmp_size) = unpack('ii', f.read(8))
            lmp_name = f.read(8)
            lmp_list.append((lmp_name, lmp_pos, lmp_size))
        for n in lmp_list:
            f.seek(n[1])
            wad_data.append((n[0], f.read(n[2])))
    #
    map_data = {}
    in_current_map = False
    for n in wad_data:
        lmp_name = n[0].decode("utf-8")
        if lmp_name == which_map:
            in_current_map = True
        elif in_current_map and lmp_name in MAP_LUMPS:
            map_data[lmp_name] = n[1]
        else:
            in_current_map = False
    return map_data


def get_linedefs(map_data):
    line_list = []
    line_data = map_data[null_pad('LINEDEFS')]
    for offset in range(0,len(line_data),14):
        (start_vertex, end_vertex, line_flags, line_special, line_tag, sidedef_front, sidedef_back) = unpack('HHhhhHH', line_data[offset:offset+14])
        line_list.append((start_vertex, end_vertex, line_flags, line_special, line_tag, sidedef_front, sidedef_back))
    return line_list


def get_sidedefs(map_data):
    side_list = []
    side_data = map_data[null_pad('SIDEDEFS')]
    for offset in range(0,len(side_data),30):
        (x_off, y_off) = unpack('hh', side_data[offset:offset+4])
        upper_tex = side_data[offset+4:offset+12]
        lower_tex = side_data[offset+12:offset+20]
        middle_tex = side_data[offset+20:offset+28]
        facing_sector = unpack('H', side_data[offset+28:offset+30])[0]
        side_list.append((x_off, y_off, upper_tex, lower_tex, middle_tex, facing_sector))
    return side_list


def get_sectors(map_data):
    sect_list = []
    sect_data = map_data[null_pad('SECTORS')]
    for offset in range(0,len(sect_data),26):
        (floor_height, ceil_height) = unpack('hh', sect_data[offset:offset+4])
        floor_flat = sect_data[offset+4:offset+12]
        ceil_flat  = sect_data[offset+12:offset+20]
        (sec_light, sec_special, sec_tag) = unpack('hhh', sect_data[offset+20:offset+26])
        sect_list.append((floor_height, ceil_height, floor_flat, ceil_flat, sec_light, sec_special, sec_tag))
    return sect_list


def get_vertexes(map_data):
    normal_verts = []
    vert_data = map_data[null_pad('VERTEXES')]
    for offset in range(0,len(vert_data),4):
        (x, y) = unpack('hh', vert_data[offset:offset+4])
        normal_verts.append([x, y])
    return normal_verts


#
# walls:   (x1, y1, x2, y2)
# portals: (x1, y1, x2, y2, sector_front, sector_back)
#
def process_map_data(line_list, side_list, vert_list, n_sectors):
    walls = []
    portals = []
    portals_by_sect = [[] for n in range(n_sectors)]
    for (start_vertex, end_vertex, line_flags, line_special, line_tag, sidedef_front, sidedef_back) in line_list:
        (x1, y1) = vert_list[start_vertex]
        (x2, y2) = vert_list[end_vertex]
        if x1 == x2 and y1 == y2:
            continue
        #
        if line_flags & ML_TWOSIDED and sidedef_front != NO_SIDEDEF and sidedef_back != NO_SIDEDEF:
            sector_front = side_list[sidedef_front][5]
            sector_back  = side_list[sidedef_back][5]
            if sector_front != sector_back:
                portals.append((x1, y1, x2, y2, sector_front, sector_back))
                portals_by_sect[sector_front].append(len(portals) - 1)
                portals_by_sect[sector_back].append(len(portals) - 1)
        #
        elif sidedef_front != NO_SIDEDEF or sidedef_back != NO_SIDEDEF:
            walls.append((x1, y1, x2, y2))
    return (walls, portals, portals_by_sect)
