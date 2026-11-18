"""Business detection thresholds. Conservative tracking also serves privacy output."""
import math

DETECTION_DEFAULTS = dict(person_confidence=.10, keypoint_confidence=.40)
DETECTION_MINIMUMS = dict(person_confidence=.10, keypoint_confidence=.25)
TRACKING_CONFIDENCE = .10
KEYPOINT_EXTRACTION_FLOOR = .25


def detection_settings(config):
    return {key: config.get(key, value) for key, value in DETECTION_DEFAULTS.items()}


def filter_persons(persons, config):
    threshold = config.get('person_confidence', DETECTION_DEFAULTS['person_confidence'])
    selected = []
    for person in persons:
        score = person.get('confidence')
        if (isinstance(score, (int, float)) and not isinstance(score, bool)
                and math.isfinite(score) and threshold <= score <= 1):
            selected.append(person)
    return selected
