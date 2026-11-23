#
# movie NFO creator
# Copyright (C) 2025 Adrien BRICCHI
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-only
#

from .util import print_error


class Rule:
    def __init__(self, key, label, check):
        self.key = key
        self.label = label
        self.check = check  # analysis -> issue data (shape defined by subclass), or falsy for no issue


class SimpleRule(Rule):
    pass  # check: analysis -> list[str] messages, or falsy for no issue


class SimpleRuleRunner:
    def __init__(self, rules):
        self.rules = rules
        self.counts = {rule.key: 0 for rule in rules}
        self.examples = {rule.key: [] for rule in rules}

    def run(self, filepath, analysis):
        for rule in self.rules:
            messages = rule.check(analysis)
            if not messages:
                continue
            self.counts[rule.key] += 1
            self.examples[rule.key].append(filepath)
            print(filepath)
            for message in messages:
                print_error("    " + message)

    def any_issues(self):
        return any(self.counts.values())

    def print_summary(self):
        for rule in self.rules:
            count = self.counts[rule.key]
            if not count:
                continue
            print(f"{rule.label}: {count}")
            for example_filepath in self.examples[rule.key][:5]:
                print("    " + example_filepath)


class RankedRule(Rule):
    def __init__(self, key, label, check, per_file_value_label, total_value_label, ranked_header, format_value):
        # check: analysis -> (list[str] messages, value) or falsy for no issue
        super().__init__(key, label, check)
        self.per_file_value_label = per_file_value_label
        self.total_value_label = total_value_label
        self.ranked_header = ranked_header
        self.format_value = format_value


class RankedRuleRunner:
    def __init__(self, rule):
        self.rule = rule
        self.count = 0
        self.total_value = 0
        self.values_by_file = []

    def run(self, filepath, analysis):
        result = self.rule.check(analysis)
        if not result:
            return

        messages, value = result
        self.count += 1
        print(filepath)
        for message in messages:
            print_error("    " + message)
        if value:
            self.total_value += value
            self.values_by_file.append((filepath, value))
            print_error(f"    {self.rule.per_file_value_label}: " + self.rule.format_value(value))

    def any_issues(self):
        return self.count > 0

    def print_summary(self):
        if not self.count:
            return
        print(f"{self.rule.label}: {self.count}")
        if self.total_value:
            print(f"{self.rule.total_value_label}: " + self.rule.format_value(self.total_value))
        if self.values_by_file:
            print(self.rule.ranked_header)
            top_values = sorted(self.values_by_file, key=lambda entry: entry[1], reverse=True)[:5]
            for top_filepath, top_value in top_values:
                print(f"    {self.rule.format_value(top_value)} - {top_filepath}")
