import glob
import importlib
import os
import sys
import numpy as np
from tqdm import tqdm
import shutil
import multiprocessing as mp
from multiprocessing.managers import BaseManager
import random
import time
from contextlib import redirect_stdout, redirect_stderr
import psutil
from pathlib import Path
import argparse

# own module
from vulcan_config_utils import CopyManager

# TODO: don't know if this is nescessary
# Limiting the number of threads
os.environ["OMP_NUM_THREADS"] = "1"


def run_vulcan(params):
    (config_file, copy_manager, std_output_dir) = params

    # get available VULCAN dir copy
    available_dir = copy_manager.get_available_copy()

    # change working directory of this process
    os.chdir(available_dir)
    sys.path.append(available_dir)

    # copy config file to VULCAN directory
    shutil.copyfile(config_file, os.path.join(available_dir, 'vulcan_cfg.py'))

    # make std_output redirect file
    cf_name = os.path.basename(config_file)
    std_output_file = os.path.join(std_output_dir, f'{cf_name[:-3]}.txt')

    # print info
    print(
        f'\n{mp.current_process()}'
        f'\non cpu {psutil.Process().cpu_num()}'
        f'\nin {os.getcwd()}'
        f'\nwith {os.path.basename(config_file)}\n'
    )

    # set this for vulcan.py
    sys.argv[0] = os.path.join(available_dir, 'vulcan.py')

    # save output to file
    with open(std_output_file, 'a+') as f:
        with redirect_stdout(f):
            with redirect_stderr(f):
                start = time.time()  # start timer

                # checks if vulcan has been imported already, because importing it runs the code
                if 'vulcan' in sys.modules.keys():
                    # reload vulcan submodules
                    loaded_modules = [k for k in sys.modules.keys()]
                    for m in loaded_modules:
                        if m == 'vulcan':
                            continue
                        elif m.startswith('vulcan'):
                            print(f'reload {m}')
                            importlib.reload(sys.modules[m])

                    # import vulcan to run it
                    importlib.reload(sys.modules['vulcan'])
                else:
                    # import vulcan to run it
                    import vulcan
                    # VSCode says import vulcan can't be resolved, but ignore this.

                ######## Don't Uncomment This!!!! 
                ##### Redundant line, VULCAN already runs in block above!!
                # exec(open(os.path.join(available_dir, "vulcan.py")).read())    # run VULCAN
                ###

                duration = (time.time() - start) / 60.
                print(f'\nVULCAN run took {duration} minutes')  # save time

    # add VULCAN dir copy back to list
    copy_manager.add_used_copy(available_dir)

    # print info
    print(
        f'exiting'
        f'\n{mp.current_process()}\n'
    )

    return duration

def string_slicer(my_str,sub):
   index=my_str.find(sub)
   if index !=-1 :
         return my_str[index:]
   else :
         raise Exception('Sub string not found!')

def main(batch_size, parallel, workers):
    # setup directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = str(Path(script_dir).parents[2])
    VULCAN_dir = os.path.join(parent_dir, 'VULCAN')
    output_dir = os.path.join(parent_dir, 'Emulator_VULCAN/data/vulcan_output')
    configs_dir = os.path.join(parent_dir, 'Emulator_VULCAN/data/configs')
    std_output_dir = os.path.join(output_dir, 'std_output')

    # TODO: create option (flag/argument) for clean start (remove outputs from previous runs)
    # Dangerous: risk of removing all output data accidentally if you don't move it first!!!

    # if clean_start:
    #     # remake output directory
    #     if os.path.isdir(output_dir):
    #         shutil.rmtree(output_dir)
    #     os.mkdir(output_dir)

    #     # remake std_output directory
    #     if os.path.isdir(std_output_dir):
    #         shutil.rmtree(std_output_dir)
    #     os.mkdir(std_output_dir)

    # load config files
    config_files = glob.glob(os.path.join(configs_dir, 'vulcan_cfg*.py'))
    print(f'Found {len(config_files)} config file(s).')

    # Checks for already run:
    # Create list of completed configs
    done_files = glob.glob(os.path.join(output_dir, 'output*.vul'))
    print(f'   Found {len(done_files)} previously run config(s).')
    # Remove prefixes & suffixes
    for i,file in enumerate(done_files):
        file = string_slicer(file,"/output_")
        file = file.removeprefix("/output_")
        file = file.removesuffix(".vul")
        done_files[i] = file
    # Cross-check with config_files list
    to_remove = []
    for file in config_files:
        filename = string_slicer(file,"/vulcan_cfg_")
        filename = filename.removeprefix("/vulcan_cfg_")
        filename = filename.removesuffix(".py")
        if filename in done_files:
            to_remove.append(file)
    # Remove flagged "to_remove" configs from config_files list
    removed = 0
    for file in to_remove:
        if file in config_files:
            config_files.remove(file)
            removed +=1

    print(f'   Removed {removed} config(s) from queue.')
    print(f'{len(config_files)} config file(s) remaining...')

    # create random batch of config files
    if batch_size:
        print(f'Using random batch of {batch_size} configs.')
        batch_files = random.sample(config_files, batch_size)
        config_files = batch_files

    if parallel:
        # number of processes
        if workers:
            num_workers = workers
        else:
            num_workers = mp.cpu_count() - 1

        # setup copy manager
        BaseManager.register('CopyManager', CopyManager)
        manager = BaseManager()
        manager.start()
        mp_copy_manager = manager.CopyManager(num_workers, VULCAN_dir)

        # make mp params
        mp_params = [(cf, mp_copy_manager, std_output_dir) for cf in config_files]

        # run mp Pool
        print(f'Running VULCAN for configs with {num_workers} workers...')
        with mp.get_context("spawn").Pool(processes=num_workers) as pool:
            results = list(tqdm(pool.imap(run_vulcan, mp_params),  # return results otherwise it doesn't work properly
                                total=len(mp_params)))
            print(f'{len(config_files)} configuration took on average {np.mean(results)} minutes.')

    else:
        # if sequential, only 1 copy
        copy_manager = CopyManager(num_workers=1, VULCAN_dir=VULCAN_dir)

        # run sequentially
        print('Running VULCAN for configs sequentially...')
        for params in tqdm(config_files):
            run_vulcan((params, copy_manager, std_output_dir))


if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(description='Run VULCAN configurations.')
    parser.add_argument('-w', '--workers', help='Number of multiprocessing-subprocesses', type=int, default=None,
                        required=False)
    parser.add_argument('-b', '--batch', help='Number of random configuration files', type=int, default=None,
                        required=False)
    parser.add_argument('-p', '--parallel', help='Whether to use multiprocessing', type=bool, default=True,
                        required=False)
    args = vars(parser.parse_args())

    # run main
    main(batch_size=args['batch'],
         parallel=args['parallel'],
         workers=args['workers'])
