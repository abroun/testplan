from typing import List

from lxml import objectify
from lxml.objectify import Element

from testplan.importers import ImportedResult, ResultImporter
from testplan.importers.base import T, ThreePhaseFileImporter
from testplan.importers.suitesresults import SuitesResult
from testplan.report import (
    TestGroupReport,
    TestReport,
    ReportCategories,
    TestCaseReport,
    RuntimeStatus,
)
from testplan.testing.multitest.entries.assertions import RawAssertion
from testplan.testing.multitest.entries.schemas.base import registry


class GTestImportedResult(SuitesResult):
    REPORT_CATEGORY = ReportCategories.GTEST


class GTestResultImporter(ThreePhaseFileImporter[Element]):
    def _read_data(self, path) -> T:
        """
        Parse XML report generated by Google test and return the root node.
        XML report should be compatible with xUnit format.

        :return: Root node of parsed raw test data
        :rtype: ``xml.etree.Element``
        """
        with open(path) as report_file:
            return objectify.parse(report_file).getroot()

    def _process_data(self, data: T) -> List[TestGroupReport]:
        """
        XML output contains entries for skipped testcases
        as well, which are not included in the report.
        """
        result: List[TestGroupReport] = []

        for suite in data.getchildren():
            suite_name = suite.attrib["name"]
            suite_report = TestGroupReport(
                name=suite_name,
                uid=suite_name,
                category=ReportCategories.TESTSUITE,
            )
            suite_has_run = False

            for testcase in suite.getchildren():

                testcase_name = testcase.attrib["name"]
                testcase_report = TestCaseReport(
                    name=testcase_name, uid=testcase_name
                )

                if not testcase.getchildren():
                    assertion_obj = RawAssertion(
                        description="Passed",
                        content="Testcase {} passed".format(testcase_name),
                        passed=True,
                    )
                    testcase_report.append(registry.serialize(assertion_obj))
                else:
                    for entry in testcase.getchildren():
                        assertion_obj = RawAssertion(
                            description=entry.tag,
                            content=entry.text,
                            passed=entry.tag != "failure",
                        )
                        testcase_report.append(
                            registry.serialize(assertion_obj)
                        )

                testcase_report.runtime_status = RuntimeStatus.FINISHED

                if testcase.attrib["status"] != "notrun":
                    suite_report.append(testcase_report)
                    suite_has_run = True

            if suite_has_run:
                result.append(suite_report)

        return result

    def _create_result(
        self, raw_data: T, processed_data: List[TestGroupReport]
    ) -> ImportedResult:
        return GTestImportedResult(
            name=self.name,
            results=processed_data,
            description=self.description,
        )