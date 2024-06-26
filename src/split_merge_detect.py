import os
import typing
import warnings

import cooler
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

from src.func_condition_wrapper import wrapper_print

warnings.simplefilter(action='ignore', category=FutureWarning)
BINSIZE_COEF = 1.5


def create_tads_tables(path_tad_1: os.path, path_tad_2: os.path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load TADs information from CSV files.

    :param path_tad_1: Path to the first TADs CSV file.
    :param path_tad_2: Path to the second TADs CSV file.
    :return tuple[pd.DataFrame, pd.DataFrame]: DataFrames containing TADs information
    """
    tad1 = pd.read_csv(path_tad_1, index_col=0)
    tad2 = pd.read_csv(path_tad_2, index_col=0)
    return tad1, tad2


def get_chrom_list(tad1: pd.DataFrame, tad2: pd.DataFrame) -> list:
    """
    Get a list of chromosomes common to both sets of TADs.

    :param tad1: DataFrame containing TADs information.
    :param tad2: DataFrame containing TADs information.
    :return list: List of common chromosomes.
    """
    tad1_chrom_list = tad1["chrom"].unique()
    tad2_chrom_list = tad2["chrom"].unique()
    if len(tad1_chrom_list) != len(tad2_chrom_list):
        warnings.warn("Different numbers of chromosomes were detected!", UserWarning)
    tad_chrom_list = [chrom for chrom in tad1_chrom_list if chrom in tad2_chrom_list]
    return tad_chrom_list


def get_chroms_coords(tad1: pd.DataFrame, tad2: pd.DataFrame, chrom: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Get TAD coordinates for a specific chromosome.

    :param tad1: DataFrame containing TADs information.
    :param tad2: DataFrame containing TADs information.
    :param chrom: Chromosome identifier.
    :return tuple[pd.DataFrame, pd.DataFrame]: DataFrames containing TAD coordinates for the specified chromosome.
    """
    tad1_chr_coords = tad1.query("chrom == @chrom")
    tad2_chr_coords = tad2.query("chrom == @chrom")
    return tad1_chr_coords, tad2_chr_coords


def modify_tads_map_by_condition(tad1_chr_coords: pd.DataFrame,
                                 binsize: int, length_flexibility: float) -> pd.DataFrame:
    """
    Increases the size of the TAD of the first card according to the condition for further search

    :param tad1_chr_coords: DataFrame containing TAD coordinates for a chromosome.
    :param binsize: Bin size.
    :param length_flexibility: Length flexibility coefficient.
    :return pd.DataFrame: Modified TADs map.
    """
    tad1_search_regs = pd.DataFrame()
    tad1_search_regs['chrom'] = tad1_chr_coords['chrom']
    tad1_search_regs['start'] = tad1_chr_coords['start'] - BINSIZE_COEF * binsize
    tad1_search_regs['end'] = tad1_chr_coords['end'] + BINSIZE_COEF * binsize
    tad1_search_regs['size'] = (tad1_chr_coords['end'] - tad1_chr_coords['start']) * length_flexibility
    return tad1_search_regs


def find_min_and_max_tad_coords(tad1_2_regions: pd.DataFrame) -> pd.DataFrame:
    """
    Find the minimum and maximum TAD coordinates.

    :param tad1_2_regions: DataFrame containing TAD coordinates.
    :return: DataFrame containing minimum and maximum TAD coordinates.
    """
    tad2_regions = pd.DataFrame
    tad2_regions['start_tad2'] = tad1_2_regions.start_tad2.min()
    tad2_regions['end_tad2'] = tad1_2_regions.end_tad2.max()
    tad2_regions['size_tad2'] = tad1_2_regions.size_tad2.sum()
    return tad2_regions


def add_size_column(tad2_chr_coords: pd.DataFrame) -> pd.DataFrame:
    """
    Add a size column to the DataFrame based on start and end coordinates.

    :param tad2_chr_coords: DataFrame containing chromosome coordinates.
    :return: DataFrame with added size column.
    """
    tad2_comp_regs = tad2_chr_coords
    tad2_comp_regs = tad2_comp_regs.assign(size=tad2_comp_regs['end'] - tad2_comp_regs['start'])
    return tad2_comp_regs


def demodify_tads_map(tads_region_intersect: pd.DataFrame, binsize: int) -> pd.DataFrame:
    """
    Demodify the TADs map by adjusting start and end coordinates.
    :param tads_region_intersect: DataFrame containing TADs region intersections.
    :param binsize: Bin size.
    :return pd.DataFrame: Demodified DataFrame with adjusted coordinates.
    """
    tads_region_intersect['start_tad1'] = tads_region_intersect['start_tad1'] + BINSIZE_COEF * binsize
    tads_region_intersect['end_tad1'] = tads_region_intersect['end_tad1'] - BINSIZE_COEF * binsize
    tads_region_intersect['size_tad1'] = tads_region_intersect['end_tad1'] - tads_region_intersect['start_tad1']
    return tads_region_intersect


def find_split(tad1_chr_coords: pd.DataFrame, tad2_chr_coords: pd.DataFrame,
               binsize: int = 100_000, length_flexibility: float = 1.1) -> pd.DataFrame:
    """
    Find split regions between TADs.

    :param tad1_chr_coords: DataFrame containing TAD coordinates for a chromosome from the first dataset.
    :param tad2_chr_coords: DataFrame containing TAD coordinates for a chromosome from the first dataset.
    :param binsize: Bin size. Defaults to 100_000.
    :param length_flexibility: Length flexibility coefficient. Defaults to 1.1.
    :return pd.DataFrame: DataFrame containing split regions.
    """
    tad1_search_regs = modify_tads_map_by_condition(tad1_chr_coords, binsize, length_flexibility)
    tad2_comp_regs = add_size_column(tad2_chr_coords)
    tads_region_intersect = pd.merge(tad1_search_regs, tad2_comp_regs, on='chrom', how='outer',
                                     suffixes=('_tad1', '_tad2'))
    tads_region_intersect = tads_region_intersect.loc[
        (tads_region_intersect.start_tad1 <= tads_region_intersect.start_tad2) &
        (tads_region_intersect.end_tad1 >= tads_region_intersect.end_tad2) &
        (tads_region_intersect.size_tad1 >= tads_region_intersect.size_tad2)]

    tads_region_intersect = tads_region_intersect[tads_region_intersect.duplicated(subset='start_tad1', keep=False)]
    tads_region_intersect_size = tads_region_intersect.groupby(['chrom', 'start_tad1', 'end_tad1', 'size_tad1']).agg(
        {'start_tad2': 'min', 'end_tad2': 'max', 'size_tad2': 'sum'})
    tads_region_intersect_size = tads_region_intersect_size.reset_index()
    tads_region_intersect_size = tads_region_intersect_size.query('size_tad1 >= size_tad2')
    tads_region_intersect = tads_region_intersect[
        tads_region_intersect['start_tad1'].isin(tads_region_intersect_size['start_tad1'])]
    return tads_region_intersect


def find_region(main_tad_coords: list, small_tads_coords: list) -> tuple:
    """
    Find the region that encompasses the main TAD and all the small TADs.

    :param main_tad_coords: Coordinates of the main TAD [chrom, start, end].
    :param small_tads_coords: Coordinates of the small TADs [[start1, end1], [start2, end2], ...].
    :return tuple: Tuple containing the region (chrom, start, end).
    """
    main_start = main_tad_coords[1]
    main_end = main_tad_coords[2]
    small_start = max([max(pair) for pair in small_tads_coords])
    small_end = min([min(pair) for pair in small_tads_coords])
    chrom = main_tad_coords[0]
    start = min([main_start, small_start])
    end = max([main_end, small_end])
    region = (chrom, start, end)
    return region


def find_coords(position: float, coords: list) -> int:
    """
    Find the index of the coordinate pair containing the given position.

    :param position: Position to find.
    :param coords: List of coordinate pairs.
    :return int: Index of the coordinate pair containing the given position.
    """
    for i, (first, second) in enumerate(coords):
        if first <= position <= second:
            return i


def calculate_pvalue(square_intensity: np.ndarray, hill_intensity: np.ndarray) -> float:
    """
    Calculate the p-value using Mann-Whitney U test.

    :param square_intensity: Intensity values for the square region.
    :param hill_intensity: Intensity values for the hill region.
    :return float: Calculated p-value.
    """
    stat, pvalue = mannwhitneyu(square_intensity, hill_intensity, method='asymptotic')
    return pvalue


def calculate_intensity(diff_matrix: pd.DataFrame, small_tads_coords: list, coords: list) -> float:
    """
    Calculate the intensity and p-value between square and hill regions.

    :param diff_matrix: Difference matrix between two contact matrices.
    :param small_tads_coords: Coordinates of the small TADs.
    :param coords: List of bin coordinates.
    :return float: Calculated p-value.
    """
    square_intensity = []
    hill_intensity = []
    for tad_id, small_tad in enumerate(small_tads_coords):
        if tad_id == (len(small_tads_coords) - 1):
            hill_intensity.extend(
                diff_matrix.iloc[start_2_corrected:end_2_corrected + 1,
                                 start_2_corrected:end_2_corrected + 1].mean().to_numpy())
            continue
        start1, end1 = small_tad[0], small_tad[1]
        start2, end2 = small_tads_coords[tad_id + 1][0], small_tads_coords[tad_id + 1][1]
        start_1_corrected, end_1_corrected = find_coords(start1, coords), find_coords(end1, coords)
        start_2_corrected, end_2_corrected = find_coords(start2, coords), find_coords(end2, coords)

        square_intensity.extend(
            diff_matrix.iloc[start_1_corrected:end_1_corrected,
                             start_2_corrected + 1:end_2_corrected + 1].mean().to_numpy())
        hill_intensity.extend(
            diff_matrix.iloc[start_1_corrected:end_1_corrected + 1,
                             start_1_corrected:end_1_corrected + 1].mean().to_numpy())

    return calculate_pvalue(square_intensity, hill_intensity)


def create_diff_matrix(main_tad_coords: list, small_tads_coords: list,
                       clr_1: cooler.Cooler, clr_2: cooler.Cooler) -> float:
    """
    Create the difference matrix and calculate intensity.

    :param main_tad_coords: Coordinates of the main TAD [chrom, start, end].
    :param small_tads_coords: Coordinates of the small TADs [[start1, end1], [start2, end2], ...].
    :param clr_1: Cooler object for the first contact matrix.
    :param clr_2: Cooler object for the second contact matrix.
    :return float: Calculated intensity.
    """
    region = find_region(main_tad_coords, small_tads_coords)
    matrix1 = clr_1.matrix(balance=False).fetch(region)
    matrix2 = clr_2.matrix(balance=False).fetch(region)
    bins = clr_1.bins().fetch(region)
    coords = list(bins[['start', 'end']].itertuples(index=False, name=None))
    diff_matrix = np.log(matrix1 + 1) - np.log(matrix2 + 1)
    diff_matrix_df = pd.DataFrame(diff_matrix, columns=coords, index=coords)
    return calculate_intensity(diff_matrix_df, small_tads_coords, coords)


def choose_region(df: pd.DataFrame, clr_1: cooler.Cooler,
                  clr_2: cooler.Cooler) -> pd.DataFrame:
    """
    Choose the regions to analyze and calculate p-values.

    :param df: DataFrame containing TAD coordinates.
    :param clr_1: Cooler object for the first contact matrix.
    :param clr_2: Cooler object for the second contact matrix.
    :return pd.DataFrame: DataFrame with added p-values.
    """
    small_tads_coords = []
    df_with_value = df
    df_with_value['pvalue'] = np.nan
    big_tad_indicies = []
    for index, row in df.iterrows():
        if index == 0:
            main_tad_coords = row[['chrom', 'start_tad1', 'end_tad1']].to_list()

        if main_tad_coords != row[['chrom', 'start_tad1', 'end_tad1']].to_list():
            pvalue = create_diff_matrix(main_tad_coords, small_tads_coords,
                                        clr_1, clr_2)
            first = big_tad_indicies[0]
            last = big_tad_indicies[-1]
            df_with_value.loc[first:last, 'pvalue'] = pvalue
            main_tad_coords = row[['chrom', 'start_tad1', 'end_tad1']].to_list()
            small_tads_coords = []
            big_tad_indicies = []

        big_tad_indicies.append(index)
        small_tads_coords.append(row[['start_tad2', 'end_tad2']].to_list())

        if index == df.index[-1]:
            pvalue = create_diff_matrix(main_tad_coords, small_tads_coords,
                                        clr_1, clr_2)
            first = big_tad_indicies[0]
            last = big_tad_indicies[-1]
            df_with_value.loc[first:last, 'pvalue'] = pvalue
    return df_with_value


def save_frame(path_save: os.path, option: str,
               saving_dataframe: pd.DataFrame, binsize: int) -> typing.NoReturn:
    """
    Save the DataFrame to a CSV file with proper naming conventions.

    :param path_save: Path to save the DataFrame.
    :param option: Option indicating split or merge.
    :param saving_dataframe: DataFrame to save.
    :param binsize: Bin size.
    :return typing.NoReturn: No return
    """
    saving_dataframe = demodify_tads_map(saving_dataframe, binsize)
    if option == "merge":
        saving_dataframe = saving_dataframe.rename(columns={"start_tad1": "start_2", "start_tad2": "start_1",
                                                            "end_tad1": "end_2", "end_tad2": "end_1"})

    else:
        saving_dataframe = saving_dataframe.rename(columns={"start_tad1": "start_1", "start_tad2": "start_2",
                                                            "end_tad1": "end_1", "end_tad2": "end_2"})
    saving_dataframe = saving_dataframe.drop(columns=['size_tad1', 'size_tad2'])
    save_name = f'{option}_coords.csv'
    save_path_df = os.path.join(path_save, save_name)
    saving_dataframe.to_csv(save_path_df)
    return


@wrapper_print
def main_split_merge_detection(clr1_filename: os.path, clr2_filename: os.path,
                               resolution: int, binsize: int,
                               path_tad_1: os.path, path_tad_2: os.path,
                               path_save: os.path = os.getcwd()) -> tuple:
    """
    Main function for split and merge detection.

    :param clr1_filename: Path to the first cooler file.
    :param clr2_filename: Path to the first cooler file.
    :param resolution: Resolution of the cooler files.
    :param binsize: Bin size.
    :param path_tad_1: Path to the first TADs CSV file.
    :param path_tad_2: Path to the first TADs CSV file.
    :param path_save: Path to save the output files. Defaults to os.getcwd().
    :return tuple: Tuple containing the counts of split and merge episodes.
    """
    clr_1 = cooler.Cooler(f'{clr1_filename}::resolutions/{resolution}')
    clr_2 = cooler.Cooler(f'{clr2_filename}::resolutions/{resolution}')
    split_merge_episodes = []
    for option in ['split', 'merge']:
        tad_split_table = pd.DataFrame()
        tad1, tad2 = create_tads_tables(path_tad_1, path_tad_2)
        if option == 'merge':
            tad1, tad2 = tad2, tad1

        tad_chrom_list = get_chrom_list(tad1, tad2)
        for chrom in tad_chrom_list:
            tad1_chr_coords, tad2_chr_coords = get_chroms_coords(tad1, tad2, chrom)
            if tad_split_table.empty is True:
                tad_split_table = find_split(tad1_chr_coords, tad2_chr_coords)
            else:
                tad_split_table = pd.concat([tad_split_table, find_split(tad1_chr_coords, tad2_chr_coords)],
                                            ignore_index=True)
        final_table = choose_region(tad_split_table, clr_1, clr_2)
        save_frame(path_save, option, final_table, binsize)
        split_merge_episodes.append(final_table[['start_tad1', 'end_tad1']].drop_duplicates().shape[0])
    return tuple(split_merge_episodes)
