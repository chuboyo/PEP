import { useMutation } from "@tanstack/react-query";

import {
  createAssignment,
  type AssignmentCreateInput,
} from "../api/assignments";

export function useCreateAssignmentMutation() {
  return useMutation({
    mutationFn: (input: AssignmentCreateInput) => createAssignment(input),
  });
}
