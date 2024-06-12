import blenderproc as bproc
import sys
import argparse
import os
import numpy as np
import random
from pathlib import Path
import json
import signal
from contextlib import contextmanager
import blenderproc.python.renderer.RendererUtility as RendererUtility
from time import time
import traceback
import bpy
import logging
import multiprocessing

# import pydevd_pycharm
# pydevd_pycharm.settrace('localhost', port=12345, stdoutToServer=True, stderrToServer=True)

# import debugpy

# debugpy.listen(5678)

# debugpy.wait_for_client()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("front_folder", help="Path to the 3D front file")
    parser.add_argument("future_folder", help="Path to the 3D Future Model folder.")
    parser.add_argument("front_3D_texture_folder", help="Path to the 3D FRONT texture folder.")
    # parser.add_argument("front_json", help="Path to a 3D FRONT scene json file, e.g.6a0e73bc-d0c4-4a38-bfb6-e083ce05ebe9.json.")
    # parser.add_argument('cc_material_folder', nargs='?', default="resources/cctextures",
    #                     help="Path to CCTextures folder, see the /scripts for the download script.")
    parser.add_argument("output_folder", help="Path to where the data should be saved")
    # parser.add_argument("--n_views_per_scene", type=int, default=100,
    #                     help="The number of views to render in each scene.")
    parser.add_argument("--append_to_existing_output", type=bool, default=True,
                        help="If append new renderings to the existing ones.")
    # parser.add_argument("--fov", type=int, default=90, help="Field of view of camera.")
    # parser.add_argument("--res_x", type=int, default=480, help="Image width.")
    # parser.add_argument("--res_y", type=int, default=360, help="Image height.")
    return parser.parse_args()


class TimeoutException(Exception): pass
@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def get_folders(args):
    front_folder = Path(args.front_folder)
    future_folder = Path(args.future_folder)
    front_3D_texture_folder = Path(args.front_3D_texture_folder)
    # cc_material_folder = Path(args.cc_material_folder)
    output_folder = Path(args.output_folder)
    if not output_folder.exists():
        output_folder.mkdir()
    return front_folder, future_folder, front_3D_texture_folder, None, output_folder


def check_name(name, category_name):
    return True if category_name in name.lower() else False

def read_scene_list(file):
        with open(file, 'r') as f:
            scenes = f.readlines()
            scenes = [i.strip('\n') for i in scenes]
            return scenes
        
        
def process_scene(rank, future_folder, front_3D_texture_folder, output_folder, front_json):
    try:
        with time_limit(600): # per scene generation would not exceeds X seconds.
            output_folder = str(output_folder) 
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            start_time = time()
            scene_name = front_json.name[:-len(front_json.suffix)]
            failed_scene_name_file = "failed_scene{}.txt".format(rank)
            export_path = scene_name + ".obj" 
            filepath=os.path.join(output_folder, export_path)
            if os.path.exists(filepath):
                return
            bproc.init()
            RendererUtility.set_max_amount_of_samples(32)

            mapping_file = bproc.utility.resolve_resource(os.path.join("front_3D", "blender_label_mapping.csv"))
            mapping = bproc.utility.LabelIdMapping.from_csv(mapping_file)


            # read 3d future model info
            with open(future_folder.joinpath('model_info_revised.json'), 'r') as f:
                model_info_data = json.load(f)
            model_id_to_label = {m["model_id"]: m["category"].lower().replace(" / ", "/") if m["category"] else 'others' for
                                m in
                                model_info_data}

            # load the front 3D objects
            loaded_objects = bproc.loader.load_front3d(
                json_path=str(front_json),
                future_model_path=str(future_folder),
                front_3D_texture_path=str(front_3D_texture_folder),
                label_mapping=mapping,
                model_id_to_label=model_id_to_label)
            # logging.error("enter blender editing.....:{}".format(scene_name))
            bpy.ops.object.select_all(action='DESELECT')
            for i in loaded_objects:
                i.blender_obj.select_set(True)
                bpy.context.view_layer.objects.active = i.blender_obj

            if bpy.ops.object.join.poll():
                bpy.ops.object.join()
                bpy.ops.object.modifier_add(type='SOLIDIFY')
                bpy.context.object.modifiers["Solidify"].thickness = 0.06
                bpy.ops.object.modifier_add(type='REMESH')
                bpy.context.object.modifiers["Remesh"].voxel_size = 0.02

            else:
                print("Objects cannot be joined.")
            
            bpy.ops.export_scene.obj(filepath=os.path.join(output_folder, export_path), use_selection=True, use_normals=False, use_uvs=False, use_materials=False, use_triangles=True)
            print('Time elapsed: %f.' % (time()-start_time))
        
    except TimeoutException as e:
        print('Time is out: %s.' % scene_name)
        with open(failed_scene_name_file, 'a') as file:
            file.write(scene_name + "\n")
        # sys.exit(0)
    except Exception as e:
        print(traceback.format_exc())
        print('Failed scene name: %s.' % scene_name)
        with open(failed_scene_name_file, 'a') as file:
            file.write(scene_name + "\n")
        # sys.exit(0)

        
        
        
if __name__ == '__main__':
    '''Parse folders / file paths'''
    logging.info("processing..............")
    args = parse_args()
    scene_list = read_scene_list("examples/datasets/front_3d_with_improved_mat/train_512_512_128.txt")
    front_folder, future_folder, front_3D_texture_folder, cc_material_folder, output_folder = get_folders(args)
    
    st_inx = 0
    ed_inx = len(scene_list)
    json_list = []
    for i in range(st_inx, ed_inx):
        front_json = front_folder.joinpath(scene_list[i] + '.json')
        json_list += [front_json]

    for front_json in json_list:
        process_scene(0, future_folder, front_3D_texture_folder, output_folder, front_json)
        
        
    # num_processes = 1
    
    # with multiprocessing.Pool(processes=num_processes) as pool:
    #     pool.starmap(process_scene, [(i % num_processes, future_folder, front_3D_texture_folder, output_folder, j) for i, j in enumerate(json_list)])


