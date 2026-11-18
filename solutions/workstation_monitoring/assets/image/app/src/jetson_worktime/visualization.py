"""Device-wide annotation palette and region opacity."""
from copy import deepcopy
import json
import math
from pathlib import Path
import re
from .localization import LocalizedError

STYLE = json.loads((Path(__file__).resolve().parents[2]/'frontend/public/overlay-style.json').read_text())
COLOR_KEYS = ('station','seat','person','skeleton','keypoint','anchor')
DEFAULT_VISUALIZATION = dict(colors={key:STYLE['colors'][key] for key in COLOR_KEYS},
                             station_fill_alpha=STYLE['station_fill_alpha'],seat_fill_alpha=STYLE['seat_fill_alpha'])


def visualization_settings(config):
    return deepcopy(config.get('visualization',DEFAULT_VISUALIZATION))


def validate_visualization(value):
    if not isinstance(value,dict) or set(value)!=set(DEFAULT_VISUALIZATION):
        raise LocalizedError('visualization.invalid')
    colors=value.get('colors')
    if not isinstance(colors,dict) or set(colors)!=set(COLOR_KEYS):
        raise LocalizedError('visualization.invalid')
    if any(not isinstance(color,str) or not re.fullmatch('#[0-9a-fA-F]{6}',color) for color in colors.values()):
        raise LocalizedError('visualization.invalid')
    for key in ('station_fill_alpha','seat_fill_alpha'):
        alpha=value[key]
        if isinstance(alpha,bool) or not isinstance(alpha,(float,int)) or not math.isfinite(alpha) or not 0<=alpha<=1:
            raise LocalizedError('visualization.invalid')
    return dict(colors={key:color.lower() for key,color in colors.items()},
                station_fill_alpha=value['station_fill_alpha'],seat_fill_alpha=value['seat_fill_alpha'])
