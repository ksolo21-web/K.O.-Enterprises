"""Shared source-coordinate mask contract for native topology operations."""
import math


def source_mask_parts(operation):
    """Return ordered rectangles; an omitted parts field retains the single box.

    Parts may overlap within an operation. Their union, never the envelope's
    interior, defines the correction area. The tight envelope defines captures.
    """
    def rectangle(value):
        return (isinstance(value, list) and len(value) == 4
                and all(type(v) in (int, float) and math.isfinite(v) for v in value)
                and value[0] < value[2] and value[1] < value[3])

    envelope = operation.get('mask_source')
    if not rectangle(envelope):
        raise ValueError('mask_source must be an ordered rectangle of four finite numbers')
    if 'mask_source_parts' not in operation:
        return [envelope]
    parts = operation['mask_source_parts']
    if not isinstance(parts, list) or not parts or not all(rectangle(part) for part in parts):
        raise ValueError('mask_source_parts must be a nonempty list of ordered finite rectangles')
    if not all(envelope[0] <= part[0] < part[2] <= envelope[2]
               and envelope[1] <= part[1] < part[3] <= envelope[3] for part in parts):
        raise ValueError('mask_source_parts must remain within mask_source envelope')
    bounds = [min(p[0] for p in parts), min(p[1] for p in parts),
              max(p[2] for p in parts), max(p[3] for p in parts)]
    if bounds != envelope:
        raise ValueError('mask_source must equal the tight mask_source_parts envelope')
    return parts


def final_mask_parts(mask):
    """Expand one project correction mask without authorizing its envelope hole."""
    values = [mask.get(key) for key in ('x', 'y', 'width', 'height')]
    if not all(type(v) in (int, float) and math.isfinite(v) for v in values):
        raise ValueError('project mask envelope must contain finite coordinates')
    x, y, width, height = values
    operation = {'mask_source': [x, y, x + width, y + height]}
    if 'parts_final' in mask:
        operation['mask_source_parts'] = mask['parts_final']
    return source_mask_parts(operation)


def transformed_source_parts(operation, transform):
    """Map declared source parts into final PDF points, with no added guard."""
    values = [transform.get(key) for key in ('scale', 'translate_x', 'translate_y')]
    if not all(type(v) in (int, float) and math.isfinite(v) for v in values) or values[0] <= 0:
        raise ValueError('source_to_final must be a finite positive uniform transform')
    scale, dx, dy = values
    return [[x0 * scale + dx, y0 * scale + dy, x1 * scale + dx, y1 * scale + dy]
            for x0, y0, x1, y1 in source_mask_parts(operation)]
