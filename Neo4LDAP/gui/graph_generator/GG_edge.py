from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsPolygonItem, QGraphicsTextItem
from PySide6.QtGui import QPen, QColor, QPolygonF
from PySide6.QtCore import QLineF, QPointF, Qt

import math

class GraphEdge(QGraphicsLineItem):
    def __init__(self, src, dst, offset=0, color=Qt.white, label=""):
        super().__init__()

        self.default_color = QColor(color)
        self.default_pen = QPen(self.default_color, 2)

        self.setPen(self.default_pen)

        self.src = src
        self.dst = dst
        
        self.label_text = label
        self.color = color
        self.offset = offset

        self.arrow_head = QGraphicsPolygonItem()
        self.arrow_head.setBrush(self.default_color)
        self.arrow_head.setPen(self.default_pen)

        self.label = QGraphicsTextItem(self.label_text)
        self.label.setDefaultTextColor(self.default_color)
        self.label.setZValue(1)

        self.src.add_edge(self)
        self.dst.add_edge(self)

        self.setAcceptHoverEvents(True)
        self.arrow_head.setAcceptHoverEvents(True)

        self.setZValue(0)
        self.arrow_head.setZValue(1)
        
    def get_nodes_math_values(self) -> tuple:
        p1 = self.src.pos()
        p2 = self.dst.pos()

        #direction
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        
        #shortest path
        length = math.hypot(dx, dy)

        #normalized vector
        ux = dx / length
        uy = dy / length

        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        
        perp_x = -uy
        perp_y = ux

        if -90 <= angle_deg <= 90 :
            effective_offset = -self.offset
        else:
            effective_offset = self.offset * 2
            angle_deg += 180

        offset_x = perp_x * effective_offset
        offset_y = perp_y * effective_offset

        return p1, p2, ux, uy, angle_deg, perp_x, perp_y, offset_x, offset_y

    def update_label_position(self, line, perp_x, perp_y, angle) -> None:
        if not self.label_text :
            return

        label_point = line.pointAt(0.42)
        bbox = self.label.boundingRect()
        anchor_x = label_point.x() - bbox.width() / 2
        anchor_y = label_point.y() - bbox.height() / 2

        # Fix vertical visual drift
        visual_align_correction = 6
        anchor_x -= perp_x * visual_align_correction
        anchor_y -= perp_y * visual_align_correction

        self.label.setPos(anchor_x, anchor_y)
        self.label.setTransformOriginPoint(bbox.width() / 2, bbox.height() / 2)
        self.label.setRotation(angle)

        if self.scene() and not self.label.scene() :
            self.scene().addItem(self.label)

    def update_arrow_position(self, end, ux, uy) -> None:
        arrow_size = 10
        point1 = QPointF(end.x() - ux * arrow_size - uy * arrow_size / 2,
                        end.y() - uy * arrow_size + ux * arrow_size / 2)
        point2 = end
        point3 = QPointF(end.x() - ux * arrow_size + uy * arrow_size / 2,
                        end.y() - uy * arrow_size - ux * arrow_size / 2)
        
        self.arrow_head.setPolygon(QPolygonF([point1, point2, point3]))

        if self.scene() :
            if self.arrow_head and not self.arrow_head.scene() :
                self.scene().addItem(self.arrow_head)

    def update_edge_position(self) -> None:
        p1, p2, ux, uy, angle_deg, perp_x, perp_y, offset_x, offset_y = self.get_nodes_math_values()

        start = QPointF(
            p1.x() + ux * self.src.radius,
            p1.y() + uy * self.src.radius
        )
        end = QPointF(
            p2.x() - ux * self.dst.radius,
            p2.y() - uy * self.dst.radius
        )

        line = QLineF(start, end)
        self.setLine(line)

        label_start = QPointF(
            p1.x() + ux * self.src.radius + offset_x,
            p1.y() + uy * self.src.radius + offset_y
        )
        label_end = QPointF(
            p2.x() - ux * self.dst.radius + offset_x,
            p2.y() - uy * self.dst.radius + offset_y
        )

        label_line = QLineF(label_start, label_end)
        self.update_label_position(label_line, perp_x, perp_y, angle_deg)
        self.update_arrow_position(end, ux, uy)