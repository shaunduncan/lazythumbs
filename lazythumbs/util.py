def scale_h_to_w(source_height, source_width, target_width):
    """
    Compute the height for an image being scaled width-wise, preserving ratio

    :param source_height: image's current height in pixels
    :param source_width: image's current width in pixels
    :param target_width: the width being scaled to
    """
    return int(source_height * (float(target_width) / source_width))
