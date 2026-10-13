import { useQuery } from "@tanstack/react-query";
import {
  Navigate,
  Outlet,
  RouterProvider,
  createBrowserRouter,
} from "react-router";
import { AppShell } from "../components/AppShell";
import { LoginPage } from "../features/auth/LoginPage";
import { RegisterPage } from "../features/auth/RegisterPage";
import { ForgotPasswordPage } from "../features/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "../features/auth/ResetPasswordPage";
import { VerifyEmailPage } from "../features/auth/VerifyEmailPage";
import { LegalPage } from "../features/auth/LegalPage";
import { HomePage } from "../features/home/HomePage";
import { MyDeskPage } from "../features/home/MyDeskPage";
import { ProfilePage } from "../features/home/ProfilePage";
import { CreateCasePage } from "../features/cases/CreateCasePage";
import { CasePage } from "../features/cases/CasePage";
import { MyCasesPage } from "../features/cases/MyCasesPage";
import { AdminCasesPage, AdminUsersPage } from "../features/admin/AdminPage";
import { ModerationQueuePage } from "../features/admin/ModerationQueuePage";
import { OfficialSourcesPage } from "../features/import/OfficialSourcesPage";
import { FBICaseBrowserPage } from "../features/import/FBICaseBrowserPage";
import { InvitationPage } from "../features/invitations/InvitationPage";
import { MemberProfilePage } from "../features/messaging/MemberProfilePage";
import { MessengerPage } from "../features/messaging/MessengerPage";
import { ProgressionPage } from "../features/progression/ProgressionPage";
import { api } from "../services/api";

function ProtectedShell() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["current-user"],
    queryFn: api.currentUser,
  });
  if (isLoading)
    return (
      <div className="grid min-h-dvh place-items-center bg-paper">
        <p className="eyebrow animate-pulse">Opening workspace</p>
      </div>
    );
  if (isError || !data) return <Navigate to="/login" replace />;
  return <AppShell />;
}

function AdminOnly() {
  const { data, isLoading } = useQuery({
    queryKey: ["current-user"],
    queryFn: api.currentUser,
  });
  if (isLoading)
    return (
      <div className="grid min-h-[50vh] place-items-center">
        <p className="eyebrow animate-pulse">Checking access</p>
      </div>
    );
  if (!data?.permissions.includes("admin.access"))
    return <Navigate to="/cases" replace />;
  return <Outlet />;
}

const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/cases" replace /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  { path: "/forgot-password", element: <ForgotPasswordPage /> },
  { path: "/reset-password", element: <ResetPasswordPage /> },
  { path: "/verify-email", element: <VerifyEmailPage /> },
  { path: "/terms", element: <LegalPage kind="terms" /> },
  { path: "/privacy", element: <LegalPage kind="privacy" /> },
  { path: "/community-standards", element: <LegalPage kind="standards" /> },
  {
    element: <AppShell />,
    children: [
      { path: "/cases", element: <HomePage /> },
      { path: "/cases/:caseId", element: <CasePage /> },
      { path: "/invite/:token", element: <InvitationPage /> },
    ],
  },
  {
    element: <ProtectedShell />,
    children: [
      { path: "/desk", element: <MyDeskPage /> },
      { path: "/my-cases", element: <MyCasesPage /> },
      { path: "/cases/new", element: <CreateCasePage /> },
      { path: "/research", element: <OfficialSourcesPage /> },
      { path: "/fbi", element: <FBICaseBrowserPage /> },
      { path: "/cases/import", element: <Navigate to="/research" replace /> },
      { path: "/cases/import/fbi", element: <Navigate to="/fbi" replace /> },
      { path: "/messages", element: <MessengerPage /> },
      { path: "/messages/:conversationId", element: <MessengerPage /> },
      { path: "/users/:userId", element: <MemberProfilePage /> },
      { path: "/profile", element: <ProfilePage /> },
      { path: "/progression", element: <ProgressionPage /> },
      {
        path: "/admin",
        element: <AdminOnly />,
        children: [
          { index: true, element: <Navigate to="/admin/users" replace /> },
          { path: "users", element: <AdminUsersPage /> },
          { path: "cases", element: <AdminCasesPage /> },
          { path: "reports", element: <ModerationQueuePage /> },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/cases" replace /> },
]);

export function App() {
  return <RouterProvider router={router} />;
}
