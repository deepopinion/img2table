# coding: utf-8
import copy
from dataclasses import dataclass
from functools import cached_property
from typing import List

import cv2
import numpy as np

from img2table.tables.metrics import compute_img_metrics
from img2table.tables.objects.cell import Cell
from img2table.tables.objects.line import Line
from img2table.tables.objects.table import Table
from img2table.tables.processing.bordered_tables.cells import get_cells
from img2table.tables.processing.bordered_tables.lines import detect_lines, threshold_dark_areas, filter_lines
from img2table.tables.processing.bordered_tables.tables import get_tables
from img2table.tables.processing.bordered_tables.tables.implicit_rows import handle_implicit_rows
from img2table.tables.processing.borderless_tables import identify_borderless_tables
from img2table.tables.processing.prepare_image import prepare_image


@dataclass
class TableImage:
    img: np.ndarray
    min_confidence: int = 50
    char_length: float = None
    median_line_sep: float = None
    thresh: np.ndarray = None
    contours: List[Cell] = None
    lines: List[Line] = None
    tables: List[Table] = None

    def __post_init__(self):
        # Prepare image by removing eventual black background
        self.img = prepare_image(img=self.img)

        # Compute image metrics
        self.char_length, self.median_line_sep, self.contours = compute_img_metrics(img=self.img)

    @cached_property
    def white_img(self) -> np.ndarray:
        white_img = copy.deepcopy(self.img)

        # Draw white rows on detected rows
        for l in self.lines:
            if l.horizontal:
                cv2.rectangle(white_img, (l.x1 - l.thickness, l.y1), (l.x2 + l.thickness, l.y2), (255, 255, 255),
                              3 * l.thickness)
            elif l.vertical:
                cv2.rectangle(white_img, (l.x1, l.y1 - l.thickness), (l.x2, l.y2 + l.thickness), (255, 255, 255),
                              2 * l.thickness)

        return white_img

    def add_borderless_header(self, tables, num_borderless_headers=1):
        # We first compute the table without the (psisible borderless) headers
        # We can then "draw" lines around the table where headers could be and 
        # detect afterwards again. This is a very simple trick to find borderless
        # headers. In case there is no header, the lines will be filtered out anyway.
        for table in tables:
            for _ in range(num_borderless_headers):
                rows = table.items

                # Each row could have merged rows, so we want to detect the height of all 
                # sub rows. Therefore, we additionally loop over all columns in a row.
                heights = []
                for row in rows:
                    heights.append(min([cell.y2 - cell.y1 for cell in row.items]))
                gap_h = int(np.mean(heights))

                # Add a row at the first position of the table
                new_row = copy.deepcopy(rows[0])
                for cell in new_row.items:
                    cell.y1 = cell.y1 - gap_h
                    cell.y2 = cell.y2 - gap_h            
                rows.insert(0, new_row)

        return tables

    def extract_bordered_tables(self, implicit_rows: bool=True, detect_borderless_headers: bool=False):
        """
        Identify and extract bordered tables from image
        :param implicit_rows: boolean indicating if implicit rows are splitted
        :param detect_borderless_headers: boolean indicating if borderless headers should be detected
        :return:
        """
        # Apply thresholding and lines filtering
        self.thresh = threshold_dark_areas(img=self.img, char_length=self.char_length)
        self.thresh = filter_lines(img=self.thresh, char_length=self.char_length)

        # Compute parameters for line detection
        minLinLength = maxLineGap = max(int(round(0.33 * self.median_line_sep)), 1) if self.median_line_sep else 10
        kernel_size = max(int(round(0.66 * self.median_line_sep)), 1) if self.median_line_sep else 20

        # Detect rows in image
        h_lines, v_lines = detect_lines(thresh=self.thresh,
                                        contours=self.contours,
                                        char_length=self.char_length,
                                        rho=0.3,
                                        theta=np.pi / 180,
                                        threshold=10,
                                        minLinLength=minLinLength,
                                        maxLineGap=maxLineGap,
                                        kernel_size=kernel_size)
        
        self.lines = h_lines + v_lines

        # Create cells from rows
        cells = get_cells(horizontal_lines=h_lines,
                          vertical_lines=v_lines)

        # Create tables from rows
        self.tables = get_tables(cells=cells,
                                 elements=self.contours,
                                 lines=self.lines,
                                 char_length=self.char_length)

        if detect_borderless_headers:
            self.tables = self.add_borderless_header(self.tables)


        # If necessary, detect implicit rows
        if implicit_rows:
            self.tables = handle_implicit_rows(img=self.white_img,
                                               tables=self.tables,
                                               contours=self.contours)

        self.tables = [tb for tb in self.tables if tb.nb_rows * tb.nb_columns >= 2]

    def extract_borderless_tables(self):
        """
        Identify and extract borderless tables from image
        :return:
        """
        # Median line separation needs to be not null to extract borderless tables
        if self.median_line_sep is not None:
            # Extract borderless tables
            borderless_tbs = identify_borderless_tables(thresh=self.thresh,
                                                        char_length=self.char_length,
                                                        median_line_sep=self.median_line_sep,
                                                        lines=self.lines,
                                                        contours=self.contours,
                                                        existing_tables=self.tables)

            # Add to tables
            self.tables += [tb for tb in borderless_tbs if tb.nb_rows >= 2 and tb.nb_columns >= 3]

    def extract_tables(self, implicit_rows:bool=False, borderless_tables:bool=False, detect_borderless_headers:bool=False) -> List[Table]:
        """
        Identify and extract tables from image
        :param implicit_rows: boolean indicating if implicit rows are splitted
        :param borderless_tables: boolean indicating if borderless tables should be detected
        :return: list of identified tables
        """
        # Extract bordered tables
        self.extract_bordered_tables(
            implicit_rows=implicit_rows, 
            detect_borderless_headers=detect_borderless_headers,
        )

        if borderless_tables:
            # Extract borderless tables
            self.extract_borderless_tables()

        return self.tables
