from constants import MONTHS
from constants import DATE_STRINGS
from constants import TIME_STRINGS
from constants import ZERO_TIMEZONE
from constants import GRASS_VERBOSITY_LELVEL_3
import os
import grass.script as grass
from metadata import get_metafile
from datetime import datetime


def validate_date_string(date_string):
    """
    """
    try:
        datetime.strptime(date_string, '%Y-%m-%d')

    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY-MM-DD")

def validate_time_string(time_string):
    """
    """
    # if 'Z' in time_string:
    #     time_string = time_string.replace('Z', ' +0000')

    try:
        if '.' in time_string:
            datetime.strptime(time_string, '%H:%M:%S.%f')
        else:
            datetime.strptime(time_string, '%H:%M:%S')

    except ValueError:
        raise ValueError("Incorrect data format, should be HH:MM:SS.ssssss")

def add_leading_zeroes(real_number, n):
     """
     Add leading zeroes to floating point numbers
     Source: https://stackoverflow.com/a/7407943
     """
     bits = real_number.split('.')
     return '{integer}.{real}'.format(integer=bits[0].zfill(n), real=bits[1])

def get_timestamp(scene, skip_microseconds=False):
    """
    Scope:  Retrieve timestamp of a Landsat scene
    Input:  Metadata *MTL.txt file
    Output: Return date, time and timezone of acquisition
    """
    metafile = get_metafile(scene)
    date_time = dict()

    try:
        metadata = open(metafile)

        for line in metadata.readlines():
            line = line.rstrip('\n')

            if len(line) == 0:
                continue

            # get Date
            if any(x in line for x in DATE_STRINGS):
                date_time['date'] = line.strip().split('=')[1].strip()
                validate_date_string(date_time['date'])

            # get Time
            if any(x in line for x in TIME_STRINGS):

                # remove " from detected line
                if('\"' in line):
                    line = line.replace('\"', '')

                # first, zero timezone if 'Z' is the last character
                if line.endswith('Z'):
                    date_time['timezone'] = ZERO_TIMEZONE

                # remove 'Z' and split the string before & after '='
                translation_table = str.maketrans('', '', 'Z')
                time = line.strip().split('=')[1].strip().translate(translation_table)

                # split string, convert to int later -- This Is Not Right
                hours, minutes, seconds = time.split('.')[0].split(':')

                if not skip_microseconds:
                    # round microseconds to six digits!
                    microseconds = float(time.split('.')[1])
                    microseconds = round((microseconds / 10000000), 6)

                    # add to seconds
                    seconds = int(seconds)
                    seconds += microseconds
                    seconds = format(seconds, '.6f')
                    seconds = add_leading_zeroes(seconds, 2)

                if float(seconds) < 10:
                    seconds = seconds.split('.')[0]

                time = ':'.join([hours, minutes, str(seconds)])
                validate_time_string(time)
                time = time.split(':')

                # create hours, minutes, seconds in date_time dictionary
                date_time['hours'] = format(int(hours), '02d')
                date_time['minutes'] = format(int(minutes), '02d')
                date_time['seconds'] = seconds # float?

    finally:
        metadata.close()

    return date_time

def build_tgis_timestamp(
        prefix,
        scene,
        timestamp,
    ):
    """
    Build and return a t.register compliant timestamp

    Parameters
    ----------
    prefix :
        Scene name prefix

    scene :
        Scene name

    timestamp :
        User-fed timestamp

    list_timestamps :
        Boolean...

    Returns
    -------
        This function does not return anything.
    """
    date = timestamp['date']
    date_Ymd = datetime.strptime(date, "%Y-%m-%d")
    date_tgis = datetime.strftime(date_Ymd, "%d %b %Y")

    hours = str(timestamp['hours'])
    minutes = str(timestamp['minutes'])
    seconds = str(timestamp['seconds'])
    timezone = timestamp['timezone']

    time = ':'.join((hours, minutes, seconds))
    string_parse_time = "%H:%M:%S"
    if '.' not in time:
        time += '.000000'
    if '.' in time:
        string_parse_time += ".%f"
    time = datetime.strptime(time, string_parse_time)
    time = datetime.strftime(time, string_parse_time)

    tgis_timestamp = str()
    # if not list_timestamps:
    #     tgis_timestamp += f'\t{date}\t{time} {timezone}\n\n'

    # else:
    #     # verbose if -t instructed
    os.environ['GRASS_VERBOSE'] = GRASS_VERBOSITY_LELVEL_3
    tgis_timestamp += f'{prefix}{scene}|{date_tgis} {time} {timezone}'

    return tgis_timestamp

def simple_timestamp(timestamp):
    """
    """
    date = timestamp['date']
    date_Ymd = datetime.strptime(date, "%Y-%m-%d")
    date_tgis = datetime.strftime(date_Ymd, "%d %b %Y")

    hours = str(timestamp['hours'])
    minutes = str(timestamp['minutes'])
    seconds = str(timestamp['seconds'])
    timezone = timestamp['timezone']

    time = ':'.join((hours, minutes, seconds))
    string_parse_time = "%H:%M:%S"
    if '.' not in time:
        time += '.000000'
    if '.' in time:
        string_parse_time += ".%f"
    time = datetime.strptime(time, string_parse_time)
    time = datetime.strftime(time, string_parse_time)
    return ' '.join((date, time, timezone))


def build_r_timestamp(timestamp):
    """
    """
    if isinstance(timestamp, dict):
        # year, month, day
        if ('-' in timestamp['date']):
            year, month, day = timestamp['date'].split('-')
        # else, if not ('-' in timestamp['date']): what?
        month = MONTHS[month]
        day_month_year = ' '.join((day, month, year))
        # hours, minutes, seconds
        hours = str(timestamp['hours'])
        minutes = str(timestamp['minutes'])
        seconds = str(timestamp['seconds'])
        hours_minutes_seconds = ':'.join((hours, minutes, seconds))
        # assembly the string
        timestamp = ' '.join((day_month_year, hours_minutes_seconds))
    return timestamp

def set_timestamp(band, timestamp):
    """
    Builds and sets the timestamp (as a string!) for a raster map
    """
    timestamp = build_r_timestamp(timestamp)
    # stamp bands
    grass.run_command('r.timestamp', map=band, date=timestamp, verbose=True)
