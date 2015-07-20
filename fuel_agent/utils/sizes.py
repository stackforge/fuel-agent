import re


class DehumanizeSize(object):
    int_float_pattern = r"(\d+(\.\d+)?)"

    def __init__(self, mapping):
        self.mapping = {}
        for keys, value in sorted(mapping, key=lambda x: x[1]):
            for key in keys:
                self.mapping[key] = value

    def __getitem__(self, key):
        return self._to_bytes(key)

    def _to_bytes(self, hvalue):
        _, value, _, unit = re.split(self.int_float_pattern, hvalue)
        return float(value) * self.mapping[unit.strip()]

SIZES = DehumanizeSize(
    (
        (('B', 'byte', 'Bi'), 1),
        (('K', 'kB', 'kilo'), 1000),
        (('M', 'MB', 'mega'), 1000**2),
        (('G', 'GB', 'giga'), 1000**3),
        (('T', 'TB', 'tera'), 1000**4),
        (('P', 'PB', 'peta'), 1000**5),
        (('E', 'EB', 'exa'), 1000**6),
        (('Z', 'ZB', 'zetta'), 1000**7),
        (('Y', 'YB', 'yotta'), 1000**8),

        (('Ki', 'kibi'), 1024),
        (('Mi', 'mebi'), 1024**2),
        (('Gi', 'gibi'), 1024**3),
        (('Ti', 'tebi'), 1024**4),
        (('Pi', 'pebi'), 1024**5),
        (('Ei', 'exbi'), 1024**6),
        (('Zi', 'zebi'), 1024**7),
        (('Yi', 'yobi'), 1024**8),
    )
)
