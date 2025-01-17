import os
import glob
from pathlib import Path
import argparse


def main(remove):
    print(f'{remove = }')

    ##################################################
    dataset = "/data" # "/data/bday_dataset"
    ##################################################
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    git_dir = str(Path(script_dir).parents[1])
    std_output = os.path.join(git_dir, f'{dataset}/vulcan_output/std_output')
    output_dir = os.path.join(git_dir, f'{dataset}/vulcan_output/')
    config_dir = os.path.join(git_dir, f'{dataset}/configs/')

    # check for missing runs
    std_out_files = glob.glob(os.path.join(std_output, '*.txt'))
    std_out_file_names = [f'{os.path.basename(f)[11:-4]}' for f in std_out_files]

    cfg_files = glob.glob(os.path.join(config_dir, '*.py'))
    cfg_file_names = [f'{os.path.basename(f)[11:-3]}' for f in cfg_files]

    output_files = glob.glob(os.path.join(output_dir, '*.vul'))
    output_file_names = [f'{os.path.basename(f)[7:-4]}' for f in output_files]

    print(f'{len(std_out_files) = }')
    print(f'{len(cfg_files) = }')
    print(f'{len(output_files) = }')

    std_not_in_output = []
    print('\nstd files not in output')
    for i, std_out_file_name in enumerate(std_out_file_names):
        if std_out_file_name not in output_file_names:
            std_not_in_output.append(std_out_files[i])
            print(f'file {i}: {std_out_file_name}')

    cfg_not_in_output = []
    print('\ncfg files not in output')
    for i, cfg_file_name in enumerate(cfg_file_names):
        if cfg_file_name not in output_file_names:
            cfg_not_in_output.append(cfg_files[i])
            print(f'file {i}: {cfg_file_name}')

    # remove missing output cfg files
    if remove:
        print(f'{len(cfg_not_in_output)} cfg files to remove...')
        for cfg_file in cfg_not_in_output:
            print(f'removing {cfg_file}')
            os.remove(cfg_file)


if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(description='Check for missing and incomplete runs')
    parser.add_argument('-r', '--remove', help='Remove cfg files of missing runs?', type=bool, default=False,
                        required=False)
    args = vars(parser.parse_args())

    main(args['remove'])
