import tempfile
import unittest
from pathlib import Path

from fraktal_ab_l5x_inventory import InventoryError, compare, inventory


def document(
    *,
    tag_access: str = ' ExternalAccess="Read/Write"',
    routine: str = '<Routine Name="Main" Type="ST"><STContent>'
                   '<Line Number="0"><![CDATA[X := 1;]]></Line></STContent></Routine>',
    task: str = '<Task Name="T" Type="PERIODIC" Rate="20" Priority="10" Watchdog="500">'
                '<ScheduledPrograms><ScheduledProgram Name="P"/></ScheduledPrograms></Task>',
    member: str = '<Member Name="Count" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false"/>',
    description: str = "<Description><![CDATA[doc]]></Description>",
    extra_tag: str = "",
) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content>
<Controller Use="Target" Name="Fixture">
<DataTypes>
<DataType Name="FRK_T_Rec" Family="NoFamily" Class="User">
<Members>
{member}
<Member Name="ZZZZZZZZZZFiller" DataType="SINT" Dimension="0" Radix="Decimal" Hidden="true"/>
</Members>
</DataType>
</DataTypes>
<AddOnInstructionDefinitions>
<AddOnInstructionDefinition Name="FRK_Aoi" Revision="1.0" ExecutePrescan="true" ExecutePostscan="false" ExecuteEnableInFalse="false">
<Parameters><Parameter Name="Rec" TagType="Base" DataType="FRK_T_Rec" Usage="InOut" Required="true"/></Parameters>
<LocalTags><LocalTag Name="Marker" DataType="DINT"/></LocalTags>
<Routines><Routine Name="Logic" Type="ST"><STContent><Line Number="0"><![CDATA[Rec.Count := 1;]]></Line></STContent></Routine></Routines>
</AddOnInstructionDefinition>
</AddOnInstructionDefinitions>
<Tags>
<Tag Name="FRK_Rec" TagType="Base" DataType="FRK_T_Rec" Constant="false"{tag_access}>
{description}
</Tag>
{extra_tag}
</Tags>
<Programs>
<Program Name="P" MainRoutineName="Main">
<Tags/>
<Routines>
{routine}
</Routines>
</Program>
</Programs>
<Tasks>
{task}
</Tasks>
</Controller>
</RSLogix5000Content>
"""


class InventoryTests(unittest.TestCase):
    def census(self, text: str):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "doc.L5X"
            path.write_text(text, encoding="utf-8")
            return inventory(path)

    def compare_documents(self, left: str, right: str):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.L5X"
            second = Path(temporary) / "second.L5X"
            first.write_text(left, encoding="utf-8")
            second.write_text(right, encoding="utf-8")
            return compare(first, second)

    def test_censuses_every_construct_family(self):
        result = self.census(document())
        self.assertEqual(list(result["DataTypes"]), ["FRK_T_Rec"])
        self.assertEqual(list(result["AddOnInstructions"]), ["FRK_Aoi"])
        self.assertEqual(list(result["ControllerTags"]), ["FRK_Rec"])
        self.assertEqual(list(result["Programs"]), ["P"])
        self.assertEqual(list(result["Tasks"]), ["T"])
        self.assertEqual(result["DescriptionCount"], 1)

    def test_hidden_backing_members_are_not_constructs(self):
        # Logix materialises a hidden member for BOOL packing; counting it
        # would make a faithful round trip look like a change
        members = self.census(document())["DataTypes"]["FRK_T_Rec"]["members"]
        self.assertEqual([member["name"] for member in members], ["Count"])

    def test_aoi_scan_flags_and_routines_are_recorded(self):
        aoi = self.census(document())["AddOnInstructions"]["FRK_Aoi"]
        self.assertEqual(aoi["executePrescan"], "true")
        self.assertEqual(aoi["executePostscan"], "false")
        self.assertEqual(aoi["localTags"], ["Marker"])
        self.assertEqual(aoi["routines"]["Logic"]["lines"], 1)

    def test_routine_bodies_are_sized_per_language(self):
        rll = document(
            routine='<Routine Name="Main" Type="RLL"><RLLContent>'
                    '<Rung Number="0" Type="N"><Text><![CDATA[NOP();]]></Text></Rung>'
                    '<Rung Number="1" Type="N"><Text><![CDATA[NOP();]]></Text></Rung>'
                    "</RLLContent></Routine>"
        )
        body = self.census(rll)["Programs"]["P"]["routines"]["Main"]
        self.assertEqual(body, {"type": "RLL", "rungs": 2})

    def test_identical_documents_are_equivalent(self):
        report = self.compare_documents(document(), document())
        self.assertTrue(report["Equivalent"], report["Differences"])

    def test_a_dropped_task_is_reported(self):
        report = self.compare_documents(document(), document(task=""))
        self.assertIn("Tasks lost in the second document: T", report["Differences"])

    def test_a_dropped_member_is_reported(self):
        report = self.compare_documents(document(), document(member=""))
        self.assertIn("DataTypes differs: FRK_T_Rec", report["Differences"])

    def test_a_lost_description_is_reported(self):
        report = self.compare_documents(document(), document(description=""))
        self.assertTrue(
            any("description count differs" in item for item in report["Differences"])
        )

    def test_an_omitted_attribute_is_not_treated_as_its_default(self):
        # Studio writes the default on export, so a generator that omits the
        # attribute differs from its own export; the tool must say so
        report = self.compare_documents(document(tag_access=""), document())
        self.assertIn("ControllerTags differs: FRK_Rec", report["Differences"])

    def test_an_added_tag_is_reported(self):
        report = self.compare_documents(
            document(),
            document(extra_tag='<Tag Name="Extra" TagType="Base" DataType="DINT"/>'),
        )
        self.assertIn(
            "ControllerTags only in the second document: Extra", report["Differences"]
        )

    def test_non_project_xml_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "not-project.L5X"
            path.write_text("<Tag/>", encoding="utf-8")
            with self.assertRaises(InventoryError):
                inventory(path)


if __name__ == "__main__":
    unittest.main()
