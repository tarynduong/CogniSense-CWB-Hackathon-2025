import { AppSidebar } from "@/components/app-sidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { getAccessToken } from "@/features/auth/auth";
import { Outlet, redirect } from "react-router";

export async function clientLoader() {
  const accessToken = getAccessToken();
  if (!accessToken) {
    throw redirect("/login");
  }
}

export default function Layout() {
  return (
    <>
      <SidebarProvider defaultOpen={true}>
        <AppSidebar />
        <SidebarInset>
          <Outlet />
        </SidebarInset>
      </SidebarProvider>
    </>
  );
}
