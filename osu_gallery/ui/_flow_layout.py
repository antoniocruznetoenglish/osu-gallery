"""A flow layout that arranges widgets in rows, wrapping to the next row when needed.

Qt does not ship a built-in flow/wrap layout (only QGridLayout, QFormLayout,
QBoxLayout, and QStackedLayout). This module provides a lightweight
``QFlowLayout`` that behaves like the classic "flow" widget used in image
gallery applications.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QWidget

logger = logging.getLogger(__name__)


class QFlowLayout(QLayout):
    """A layout that wraps items into rows, like text flowing on a page.

    Items are added with :meth:`addWidget` or :meth:`addItem`. When the window
    is resized the items are reflowed into rows based on the available width.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        margin: int | None = None,
        h_spacing: int = -1,
        v_spacing: int = -1,
        columns: int = 0,
    ) -> None:
        """Create the flow layout.

        Parameters
        ----------
        parent:
            The parent widget.
        margin:
            Uniform margin in pixels around the layout. Defaults to 4.
        h_spacing:
            Horizontal spacing between items in pixels, or ``-1`` for default.
        v_spacing:
            Vertical spacing between rows in pixels, or ``-1`` for default.
        columns:
            Fixed number of columns to display. If 0, items wrap based on
            available width. If > 0, items are sized to fill exactly this
            many columns.
        """
        super().__init__(parent)

        if margin is not None:
            self._margins = QMargins(margin, margin, margin, margin)
        else:
            self._margins = QMargins(4, 4, 4, 4)

        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._fixed_columns = columns
        self._items: list[QLayoutItem] = []

    # -- QLayout overrides --

    def addItem(self, item: QLayoutItem) -> None:
        """Append *item* to the end of the layout."""
        self._items.append(item)
        logger.debug("Added item to flow layout (total: %d)", len(self._items))

    def count(self) -> int:
        """Return the number of items in the layout."""
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        """Return the item at *index*, or ``None`` if out of range."""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        """Remove and return the item at *index*, or ``None`` if out of range."""
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        """The layout can grow in both horizontal and vertical directions."""
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        """Height depends on width for flow layouts."""
        return True

    def heightForWidth(self, width: int) -> int:
        """Compute the preferred height for the given width."""
        return self._do_layout(QRect(0, 0, width, 0), test_only=True).height()

    def setGeometry(self, rect: QRect) -> None:
        """Lay out items within *rect*."""
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        """Return the suggested size for the layout."""
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        """Return the minimum size the layout can shrink to."""
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom(),
        )
        return size

    # -- Public helpers --

    def addWidget(self, widget: QWidget) -> None:
        """Shorthand for ``addItem(QWidgetItem(widget))``."""
        super().addWidget(widget)

    def addWidgets(self, widgets: Sequence[QWidget]) -> None:
        """Add multiple widgets to the layout."""
        for widget in widgets:
            self.addWidget(widget)

    def clear(self) -> None:
        """Remove all items from the layout and hide/delete their widgets."""
        while self._items:
            item = self._items.pop(0)
            try:
                widget = item.widget()
                if widget:
                    widget.hide()
                    widget.deleteLater()
            except RuntimeError:
                pass

    # -- Internal --

    def _do_layout(self, rect: QRect, *, test_only: bool) -> QRect:
        """Perform the actual flow layout.

        Parameters
        ----------
        rect:
            The available rectangle to lay items into.
        test_only:
            If ``True``, only compute positions without moving items.

        Returns
        -------
        QRect
            The rectangle occupied by the laid-out items.
        """
        margins = self.contentsMargins()
        margin_left = margins.left()
        margin_top = margins.top()
        margin_right = margins.right()
        margin_bottom = margins.bottom()
        effective_rect = rect.adjusted(margin_left, margin_top, -margin_right, -margin_bottom)

        cursor_x = effective_rect.left()
        cursor_y = effective_rect.top()

        if self._fixed_columns > 0:
            h_spacing = self._h_spacing if self._h_spacing >= 0 else 0
            v_spacing = self._v_spacing if self._v_spacing >= 0 else 0
            available_width = effective_rect.width()
            total_spacing = h_spacing * (self._fixed_columns - 1)
            item_width = (available_width - total_spacing) // self._fixed_columns

            for item in self._items:
                widget = item.widget()
                if widget is not None:
                    pass

                item_height = item.sizeHint().height()
                next_x = cursor_x + item_width + h_spacing

                if next_x - h_spacing > effective_rect.right() and cursor_x > effective_rect.left():
                    cursor_x = effective_rect.left()
                    cursor_y += self._line_height + v_spacing

                item_rect = QRect(
                    QPoint(cursor_x, cursor_y),
                    QSize(item_width, item_height),
                )
                if not test_only:
                    item.setGeometry(item_rect)
                    if widget is not None:
                        widget.setFixedSize(item_width, item_height)

                cursor_x += item_width + h_spacing

            content_bottom = cursor_y + self._line_height
            margins = self.contentsMargins()
            total_height = content_bottom - rect.top() + margins.bottom()
            return QRect(
                QPoint(effective_rect.left(), rect.top()),
                QSize(rect.width(), max(total_height, 0)),
            )

        for item in self._items:
            widget = item.widget()
            if widget is not None:
                h_spacing = self._h_spacing if self._h_spacing >= 0 else 0
                v_spacing = self._v_spacing if self._v_spacing >= 0 else 0
            else:
                h_spacing = self._h_spacing if self._h_spacing >= 0 else item.spacing()
                v_spacing = self._v_spacing if self._v_spacing >= 0 else item.spacing()

            item_width = item.sizeHint().width()
            next_x = cursor_x + item_width + h_spacing

            if next_x - h_spacing > effective_rect.right() and cursor_x > effective_rect.left():
                cursor_x = effective_rect.left()
                cursor_y += self._line_height + v_spacing

            if not test_only:
                item.setGeometry(QRect(QPoint(cursor_x, cursor_y), item.sizeHint()))

            cursor_x += item_width + h_spacing

        content_bottom = cursor_y + self._line_height
        margins = self.contentsMargins()
        total_height = content_bottom - rect.top() + margins.bottom()
        return QRect(
            QPoint(effective_rect.left(), rect.top()),
            QSize(rect.width(), max(total_height, 0)),
        )

    @property
    def _line_height(self) -> int:
        """Return the maximum height of any item in the layout."""
        max_h = 0
        for item in self._items:
            max_h = max(max_h, item.sizeHint().height())
        return max_h
