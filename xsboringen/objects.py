# -*- coding: utf-8 -*-
# Tom van Steijn, Royal HaskoningDHV

from collections import Iterable
from itertools import groupby


class AsDictMixin(object):
    '''Mixin for mapping class attributes to dictionary'''
    def as_dict(self, keys=None):
        if keys:
            return {k: getattr(self, k) for k in keys}
        else:
            return {k: v for k, v in self.__dict__.items()
                if not k.startswith('__')}


class Segment(AsDictMixin):
    '''Class representing borehole segment'''
    def __init__(self, top, base, lithology,
            sandmedianclass=None, **attrs):
        self.top = top
        self.base = base
        self.lithology = lithology
        self.sandmedianclass = sandmedianclass

        # set other properties
        for key, value in attrs.items():
            setattr(self, key, value)

    def __repr__(self):
        return 'Segment(top={:.2f}, base={:.2f}, lithology={!s})'.format(
            self.top,
            self.base,
            self.lithology,
            )

    def __iadd__(self, other):
        self.top = min(self.top, other.top)
        self.base = max(self.base, other.base)
        return self

    @property
    def thickness(self):
        '''thickness of segment'''
        return self.base - self.top

    def relative_to(self, z):
        '''return top and base relative to z'''
        return z - self.top, z - self.base


class Borehole(AsDictMixin, Iterable):
    '''Borehole class with iterator method yielding segments'''
    def __init__(self, code, depth,
            x=None, y=None, z=None,
            segments=None, verticals=None,
            **attrs,
            ):
        self.code = code
        self.depth = depth

        self.x = x
        self.y = y
        self.z = z

        self.segments = segments
        self.verticals = verticals

        # set other properties
        for key, value in attrs.items():
            setattr(self, key, value)

        self.materialized = False

        self.key = lambda s: {
            'lithology': s.lithology,
            'sandmedianclass': s.sandmedianclass,
            }

    def __repr__(self):
        return 'Borehole(code={!s}, depth={:.2f})'.format(
            self.code,
            self.depth,
            )

    def __len__(self):
        if hasattr(self.segments, "__len__"):
            return len(self.segments)
        else:
            raise AttributeError('segments generator has no length')

    def __iter__(self):
        for segment in self.segments:
            yield segment

    @property
    def geometry(self):
        '''borehole geometry interface'''
        return {'type': 'Point', 'coordinates': (self.x, self.y)}

    @property
    def has_xy(self):
        return (self.x is not None) and (self.y is not None)

    @property
    def has_z(self):
        return (self.z is not None)

    def materialize(self):
        '''read borehole segments and assign as list'''
        segments_in_list = []
        for segment in self.segments:
            segments_in_list.append(segment)
        self.segments = segments_in_list
        self.materialized = True

    def simplify(self, min_thickness=None):
        '''combine segments with same lithology and sandmedianclasses'''
        simple_segments = []

        for i, (key, grouped) in enumerate(groupby(self.segments, self.key)):
            grouped_segments = [s for s in grouped]
            simplified = Segment(
                top=min(s.top for s in grouped_segments),
                base=max(s.base for s in grouped_segments),
                **key,
                )
            simple_segments.append(simplified)
        self.segments = simple_segments
        self.materialized = True

        if min_thickness is not None:
            self._apply_min_thickness(min_thickness)
            self.simplify(min_thickness=None)

    def _get_min_thickness(self):
        return min((s.thickness, i) for i, s in enumerate(self.segments))

    def _apply_min_thickness(self, min_thickness):
        smallest_thickness, idx = self._get_min_thickness()
        while smallest_thickness < min_thickness:
            if idx > 0:
                segment_above = self.segments[idx - 1]
            else:
                segment_above = None
            try:
                segment_below = self.segments[idx + 1]
            except IndexError:
                segment_below = None
            if (segment_above is None) and (segment_below is None):
                break
            elif not smallest_thickness > 0.:
                del self.segments[idx]
            elif segment_above is None:
                self.segments[idx + 1].top = self.segments[idx].top
                del self.segments[idx]
            elif segment_below is None:
                self.segments[idx - 1].base = self.segments[idx].base
                del self.segments[idx]
            elif segment_above.thickness < segment_below.thickness:
                self.segments[idx - 1].base = self.segments[idx].base
                del self.segments[idx]
            else:
                self.segments[idx + 1].top = self.segments[idx].top
                del self.segments[idx]
        smallest_thickness, idx = self._get_min_thickness()

class CPT(Borehole):
    '''CPT class equal to borehole'''
    pass