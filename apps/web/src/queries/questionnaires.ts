import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createQuestionnaire,
  listQuestionnaireTemplates,
  listQuestionnaires,
  updateQuestionnaire,
  type QuestionnaireCreateInput,
  type QuestionnaireUpdateInput,
} from "../api/questionnaires";

export const questionnairesQueryKey = ["questionnaires"] as const;
export const questionnaireTemplatesQueryKey = [
  "questionnaire-templates",
] as const;

export function useQuestionnairesQuery(enabled: boolean) {
  return useQuery({
    queryKey: questionnairesQueryKey,
    queryFn: listQuestionnaires,
    enabled,
  });
}

export function useQuestionnaireTemplatesQuery(enabled: boolean) {
  return useQuery({
    queryKey: questionnaireTemplatesQueryKey,
    queryFn: listQuestionnaireTemplates,
    enabled,
  });
}

export function useCreateQuestionnaireMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: QuestionnaireCreateInput) => createQuestionnaire(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: questionnairesQueryKey });
    },
  });
}

export function useUpdateQuestionnaireMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string;
      input: QuestionnaireUpdateInput;
    }) => updateQuestionnaire(id, input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: questionnairesQueryKey });
    },
  });
}
