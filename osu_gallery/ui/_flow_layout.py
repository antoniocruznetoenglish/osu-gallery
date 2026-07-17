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
    ) -> None:
        super().__init__(parent)

        if margin is not None:
            self._margins = QMargins(margin, margin, margin, margin)
        else:
            self._margins = QMargins(4, 4, 4, 4)

        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
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
        """Remove all items from the layout and delete them."""
        while self._items:
            item = self._items.pop(0)
            self.removeItem(item)
            try:
                if widget := item.widget():
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
        """
        margins = self.contentsMargins()
        left, top, right, bottom = margins.left(), margins.top(), margins.right(), margins.bottom()
        effective = rect.adjusted(left, top, -right, -bottom)

        x = effective.left()
        y = effective.top()

        for item in self._items:
            widget = item.widget()
            if widget is not None:
                spacing_h = self._h_spacing if self._h_spacing >= 0 else 0
                spacing_v = self._v_spacing if self._v_spacing >= 0 else 0
            else:
                spacing_h = self._h_spacing if self._h_spacing >= 0 else item.spacing()
                spacing_v = self._v_spacing if self._v_spacing >= 0 else item.spacing()

            next_x = x + item.sizeHint().width() + spacing_h

            if next_x - spacing_h > effective.right() and x > effective.left():
                x = effective.left()
                y += self._line_height + spacing_v

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x += item.sizeHint().width() + spacing_h

        return QRect(QPoint(effective.left(), y), QSize())

    @property
    def _line_height(self) -> int:
        """Return the maximum height of any item in the layout."""
        max_h = 0
        for item in self._items:
            max_h = max(max_h, item.sizeHint().height())
        return max_h
