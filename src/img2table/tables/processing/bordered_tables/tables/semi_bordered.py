# coding: utf-8
from typing import List

import numpy as np

from img2table.tables.objects.cell import Cell
from img2table.tables.objects.line import Line


def add_semi_bordered_cells(cluster: List[Cell], lines: List[Line], char_length: float):
    """
    Identify and add semi-bordered cells to cluster
    :param cluster: cluster of cells
    :param lines: lines in image
    :param char_length: average character length
    :return: cluster with add semi-bordered cells
    """
    # Compute cluster coordinates
    x_min, x_max = min([c.x1 for c in cluster]), max([c.x2 for c in cluster])
    y_min, y_max = min([c.y1 for c in cluster]), max([c.y2 for c in cluster])

    # Initialize new coordinates
    new_x_min, new_x_max, new_y_min, new_y_max = x_min, x_max, y_min, y_max

    # Find horizontal lines of the cluster
    y_values_cl = {c.y1 for c in cluster}.union({c.y2 for c in cluster})
    h_lines = [line for line in lines if line.horizontal
               and min(line.x2, x_max) - max(line.x1, x_min) >= 0.8 * (x_max - x_min)
               and min([abs(line.y1 - y) for y in y_values_cl]) <= 0.05 * (y_max - y_min)]
    
    # Note: We ignore the original algorithm and take the outher hull instead. 
    # This also detects tables like case 8 as shown in the TestCases.pdf file

    # Find vertical lines of the cluster
    x_values_cl = {c.x1 for c in cluster}.union({c.x2 for c in cluster})
    v_lines = [line for line in lines if line.vertical
               and min(line.y2, y_max) - max(line.y1, y_min) >= 0.8 * (y_max - y_min)
               and min([abs(line.x1 - x) for x in x_values_cl]) <= 0.05 * (x_max - x_min)]

    all_lines = h_lines + v_lines
    new_x_min = min([l.x1 for l in all_lines])
    new_x_max = max([l.x2 for l in all_lines])
    new_y_min = min([l.y1 for l in all_lines])
    new_y_max = max([l.y2 for l in all_lines])

    # Create new cells around the table
    new_y_values = sorted(list(y_values_cl.union({new_y_min, new_y_max})))
    new_x_values = sorted(list(x_values_cl.union({new_x_min, new_x_max})))

    left_cells = [Cell(x1=new_x_min, x2=x_min, y1=y_top, y2=y_bottom)
                  for y_top, y_bottom in zip(new_y_values, new_y_values[1:])]
    right_cells = [Cell(x1=x_max, x2=new_x_max, y1=y_top, y2=y_bottom)
                   for y_top, y_bottom in zip(new_y_values, new_y_values[1:])]
    top_cells = [Cell(x1=x_left, x2=x_right, y1=new_y_min, y2=y_min)
                 for x_left, x_right in zip(new_x_values, new_x_values[1:])]
    bottom_cells = [Cell(x1=x_left, x2=x_right, y1=y_max, y2=new_y_max)
                    for x_left, x_right in zip(new_x_values, new_x_values[1:])]

    # Update cluster cells
    cluster_cells = {c for c in cluster + left_cells + right_cells + top_cells + bottom_cells if c.area > 20}

    return list(cluster_cells)
