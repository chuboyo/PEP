import { Navigate, Route, Routes } from "react-router-dom";

import { AcceptInvitePage } from "./pages/AcceptInvitePage";
import { AdminClubsListPage } from "./pages/AdminClubsListPage";
import { AdminClubsPage } from "./pages/AdminClubsPage";
import { ClubCoachesPage } from "./pages/ClubCoachesPage";
import { CreateQuestionnairePage } from "./pages/CreateQuestionnairePage";
import { CreateTeamPage } from "./pages/CreateTeamPage";
import { EditQuestionnairePage } from "./pages/EditQuestionnairePage";
import { HomePage } from "./pages/HomePage";
import { InvitePlayerPage } from "./pages/InvitePlayerPage";
import { LoginPage } from "./pages/LoginPage";
import { QuestionnairesPage } from "./pages/QuestionnairesPage";
import { TeamDetailPage } from "./pages/TeamDetailPage";
import { TeamsPage } from "./pages/TeamsPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/accept-invite" element={<AcceptInvitePage />} />
      <Route path="/admin/clubs" element={<AdminClubsListPage />} />
      <Route path="/admin/clubs/new" element={<AdminClubsPage />} />
      <Route path="/club/coaches" element={<ClubCoachesPage />} />
      <Route path="/teams" element={<TeamsPage />} />
      <Route path="/teams/new" element={<CreateTeamPage />} />
      <Route path="/teams/:teamId" element={<TeamDetailPage />} />
      <Route
        path="/teams/:teamId/players/new"
        element={<InvitePlayerPage />}
      />
      <Route path="/questionnaires" element={<QuestionnairesPage />} />
      <Route path="/questionnaires/new" element={<CreateQuestionnairePage />} />
      <Route
        path="/questionnaires/:questionnaireId/edit"
        element={<EditQuestionnairePage />}
      />
      <Route path="/" element={<HomePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
