#!/usr/bin/env python
import argparse
import numpy as np
import time

from source.wad_func  import get_map_lmps, get_linedefs, get_sidedefs, get_sectors, get_vertexes, process_map_data, write_reject

UNKNOWN = 0
VISIBLE = 1
HIDDEN  = 2


def main(raw_args=None):
    parser = argparse.ArgumentParser(description='los-reject', formatter_class=argparse.ArgumentDefaultsHelpFormatter,)
    parser.add_argument('-i', type=str, required=True,  metavar='input.wad',  help="* Input WAD")
    parser.add_argument('-m', type=str, required=True,  metavar='MAP01',      help="* Map name")
    parser.add_argument('-o', type=str, required=True,  metavar='REJECT.lmp', help="* Output reject table lmp")
    args = parser.parse_args(raw_args)
    #
    IN_WAD = args.i
    WHICH_MAP = args.m
    OUT_REJECT = args.o

    map_data = get_map_lmps(IN_WAD, WHICH_MAP)
    if not map_data:
        print(f'Error: {WHICH_MAP} not found.')
        exit(1)
    line_list = get_linedefs(map_data)
    side_list = get_sidedefs(map_data)
    sect_list = get_sectors(map_data)
    vert_list = get_vertexes(map_data)
    n_sectors = len(sect_list)
    (walls, portals, portals_by_sect) = process_map_data(line_list, side_list, vert_list, n_sectors)
    print(f'{n_sectors} sectors / {len(line_list)} lines / {len(walls)} walls / {len(portals)} portals')
    del line_list, side_list, sect_list, vert_list

    tt = time.perf_counter()
    reject = np.full((n_sectors, n_sectors), UNKNOWN, dtype='B')

    # mark all sectors visible to themselves
    for i in range(n_sectors):
        reject[i,i] = VISIBLE

    # mark all sectors visible to their immediate neighbors
    for (_, _, _, _, sector_front, sector_back) in portals:
        reject[sector_front,sector_back] = VISIBLE
        reject[sector_back,sector_front] = VISIBLE

    # do visibility tests on the rest
    sort_keys = [(-len(portals_by_sect[si]), si) for si in range(n_sectors)]
    for (i_si, (n, si)) in enumerate(sorted(sort_keys)):
        #
        # BIG TODO
        #
        print(f'sector {i_si+1} / {n_sectors} ({time.perf_counter() - tt:.1f} sec)')

    reject_out = reject != VISIBLE # byte array --> bool array
    n_hidden = int(np.sum(reject_out))
    print(f'{n_hidden} / {n_sectors*n_sectors} sector pairs hidden ({100.0*n_hidden/(n_sectors*n_sectors):.1f}%) ({time.perf_counter() - tt:.1f} sec)')

    write_reject(reject_out, OUT_REJECT)


if __name__ == '__main__':
    main()
