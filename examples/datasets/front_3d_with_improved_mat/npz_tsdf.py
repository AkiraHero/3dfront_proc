import os
import multiprocessing
from tqdm import tqdm
import sys
import numpy as np
import struct


def get_sdf(file):
    with open(file, 'rb') as f:
        buf = f.read(4 * 3)
        shape = np.array(struct.unpack('iii', buf))
        buf = f.read(4 * 3)
        min_box = np.array(struct.unpack('fff', buf))
        buf = f.read(4)
        voxel_size = struct.unpack('f', buf)
        buf = f.read()
        data = struct.unpack('f' * np.prod(shape), buf)
        tsdf = np.array(data).reshape(shape[::-1])
        tsdf = tsdf.transpose(2, 1, 0)
        data_dict = {
            'sdf': tsdf,
            'origin': min_box,
            'voxel_size': voxel_size,
            'dim': shape,
        }
        return data_dict
    

def process_file(mesh_obj):
    sdf_file = os.path.join(sdf_dir, mesh_obj)
    res_dir = os.path.join(out_dir, mesh_obj.split(".")[0])
    if not os.path.exists(res_dir):
        os.makedirs(res_dir)
    final_file_tsdf = os.path.join(res_dir, "tsdf_v2.npz")
    if os.path.exists(sdf_file) and not os.path.exists(final_file_tsdf):
        data = get_sdf(sdf_file)
        sdf = data['sdf']
        voxel_size = data['voxel_size'][0]
        tsdf = sdf / (voxel_size * 3)
        tsdf[tsdf>1] = 1
        tsdf[tsdf<-1] = -1
        data['tsdf'] = tsdf
        data.pop('sdf')
        np.savez_compressed(final_file_tsdf, **data)


if __name__ == '__main__':
    sdf_dir = sys.argv[1]
    out_dir = sys.argv[2]
    sdf_files = os.listdir(sdf_dir)
    sdf_files = [i for i in sdf_files if i.endswith(".sdf")]
    sdf_files.sort()

    pool = multiprocessing.Pool(processes=2)
    with tqdm(total=len(sdf_files), desc="Processing") as pbar:
        for _ in pool.imap_unordered(process_file, sdf_files):
            pbar.update(1)
            

