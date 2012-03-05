import re

def geometry_parse(action, geo_str, exc):
    if action == 'thumbnail':
        width_match = re.match('^(\d+)$', geo_str)
        height_match = re.match('^x(\d+)$', geo_str)
        width, height = (
             width_match.groups()[0] if width_match else None,
             height_match.groups()[0] if height_match else None
        )
        if width is None and height is None:
            raise exc('must supply either a height or a width for thumbnail')

        return width, height

    if action in ('resize', 'scale'):
        wh_match = re.match('^(\d+)x(\d+)', geo_str)
        if not wh_match:
            raise exc('both width and height required for %s' % action)
        return wh_match.groups()
