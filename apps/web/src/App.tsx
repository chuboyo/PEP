import { Navigate, Route, Routes } from "react-router-dom";

import { AcceptInvitePage } from "./pages/AcceptInvitePage";
import { AdminClubsListPage } from "./pages/AdminClubsListPage";
import { AdminClubsPage } from "./pages/AdminClubsPage";
import { ClubCoachesPage } from "./pages/ClubCoachesPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/accept-invite" element={<AcceptInvitePage />} />
      <Route path="/admin/clubs" element={<AdminClubsListPage />} />
      <Route path="/admin/clubs/new" element={<AdminClubsPage />} />
      <Route path="/club/coaches" element={<ClubCoachesPage />} />
      <Route path="/" element={<HomePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
