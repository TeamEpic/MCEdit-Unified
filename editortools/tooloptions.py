#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from glbackground import Panel


class ToolOptions(Panel):
    def key_down(self, evt):
        if self.root.getKey(evt) == 'Escape':
            self.escape_action()

    def escape_action(self, *args, **kwargs):
        self.dismiss()

