import { listExerciseTypes, listGrades, listGrammarTopics, listUnitsForGrade } from "./catalog";

export interface DashboardData {
  gradeCount: number;
  unitCount: number;
  grammarPointCount: number;
  exerciseTypeCount: number;
  grade7Unit3Title: string | undefined;
}

/** Gọi song song các endpoint catalog để chứng minh backend<->frontend đã nối thông suốt. */
export async function fetchDashboardData(): Promise<DashboardData> {
  const [grades, grammarTopics, exerciseTypes] = await Promise.all([
    listGrades(),
    listGrammarTopics(),
    listExerciseTypes(),
  ]);

  const grade7 = grades.find((g) => g.number === 7);
  const grade7Units = grade7 ? await listUnitsForGrade(grade7.id) : [];
  const unitTotals = await Promise.all(
    grades
      .filter((g) => g.number >= 6 && g.number <= 12)
      .map((g) => listUnitsForGrade(g.id).then((units) => units.length)),
  );

  const grammarPointCount = grammarTopics.reduce(
    (total, topic) => total + topic.groups.reduce((sum, group) => sum + group.points.length, 0),
    0,
  );

  return {
    gradeCount: grades.length,
    unitCount: unitTotals.reduce((a, b) => a + b, 0),
    grammarPointCount,
    exerciseTypeCount: exerciseTypes.length,
    grade7Unit3Title: grade7Units.find((u) => u.order_no === 3)?.title,
  };
}
