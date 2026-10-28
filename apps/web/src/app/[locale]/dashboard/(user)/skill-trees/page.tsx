import { getMetadata } from "~/lib/metadata";
import {
  DashboardHeader,
  DashboardHeaderDescription,
  DashboardHeaderTitle,
} from "~/modules/common/layout/dashboard/header";
import { SkillTreeAppLoader } from "~/modules/skill-tree/components/SkillTreeAppLoader";

export const generateMetadata = getMetadata({
  title: "Skill Trees",
  description: "Interactive climbing skill tree with unlock progress",
});

export default function SkillTreesPage() {
  return (
    <>
      <DashboardHeader>
        <div>
          <DashboardHeaderTitle>Skill Trees</DashboardHeaderTitle>
          <DashboardHeaderDescription>
            Track climbing milestones, actions, and unlock progress.
          </DashboardHeaderDescription>
        </div>
      </DashboardHeader>

      <SkillTreeAppLoader />
    </>
  );
}
