import sys
import time
import traceback
import typing

FUNC_NAMES = {'count_tads_change_intensity': ['Searching changes in the intensity of TADs...',
                                              'The number of TADs with a changed intensity: '],
              'main_split_merge_detection': ['Searching splits and merges in TADs...',
                                             'The number of splits|merges: ']
              }


def wrapper_print(func: typing.Callable) -> typing.Callable:
    """
    Decorator function to print progress messages and results of the decorated function.

    :param func: The function to be decorated.
    :return typing.Callable: The decorated function.
    """
    def wrapper(*args, **kwargs) -> typing.NoReturn:
        """
        Wrapper function to print progress messages and results.

        :param args: Variable length argument list.
        :param kwargs: Arbitrary keyword arguments.
        :return typing.NoReturn: No return value.
        """
        sys.stderr.write(f'{FUNC_NAMES[func.__name__][0]}\r')
        sys.stderr.flush()
        try:
            result = func(*args, **kwargs)
            sys.stderr.write(f'Completed successfully!                       \r')
            sys.stderr.flush()
            time.sleep(2)
            sys.stdout.write(f'{FUNC_NAMES[func.__name__][1]}{result}\n')
            sys.stdout.flush()
            time.sleep(2)
        except Exception as e:
            sys.stderr.write(traceback.format_exc())
    return wrapper


def visualise_wrapper(func: typing.Callable) -> typing.Callable:
    """
    Decorator function to perform visualization.

    :param func: The function to be decorated.
    :return typing.Callable: The decorated function.
    """
    def wrapper_first(*args, **kwargs) -> typing.NoReturn:
        """
        Wrapper function to perform visualization.

        :param args: Variable length argument list.
        :param kwargs: Arbitrary keyword arguments.
        :return typing.NoReturn: No return value.
        """
        if not wrapper_first.used:
            wrapper_first.used = True
            sys.stderr.write(f'Visualising...\r')
            sys.stderr.flush()
        func(*args, **kwargs)

    wrapper_first.used = False
    return wrapper_first


def parser_wrapper(func: typing.Callable) -> typing.Callable:
    """
    Decorator function to handle parsing.

    :param func: The function to be decorated.
    :return typing.Callable: The decorated function.
    """
    def wrapper_2(*args, **kwargs) -> typing.NoReturn:
        """
        Wrapper function to handle parsing.

        :param args: Variable length argument list.
        :param kwargs: Arbitrary keyword arguments.
        :return typing.NoReturn: No return value.
        """
        output_directory, map1_tad_count, map2_tad_count = func(*args, **kwargs)
        sys.stderr.write(f'CTADO completed successfully!\n')
        sys.stderr.flush()
        sys.stdout.write(f'Total TADs count on first|second map: {(map1_tad_count, map2_tad_count)}\n')
        sys.stdout.flush()
        sys.stdout.write(f'Output location:\n{output_directory}')
    return wrapper_2
