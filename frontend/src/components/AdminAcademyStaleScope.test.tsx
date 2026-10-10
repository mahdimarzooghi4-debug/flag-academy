import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminAcademyOperationsWorkspace } from "./AdminAcademyOperationsWorkspace";

const network = vi.hoisted(() => ({
  GET: vi.fn(),
  POST: vi.fn(),
}));
vi.mock("../api/client", () => ({
  makeApi: () => ({ GET: network.GET, POST: network.POST }),
}));

afterEach(() => {
  cleanup();
  network.GET.mockReset();
  network.POST.mockReset();
});

const cohort = {
  cohort_id: "cohort-a",
  code: "A",
  name: "گروه واقعی",
  track_code: "PRODUCT",
  status: "ACTIVE",
};
const classA = {
  class_offering_id: "class-a",
  cohort_id: "cohort-a",
  title: "کلاس مجاز",
  primary_capability_version_id: "version-a",
  status: "ACTIVE",
};
const rosterA = {
  class_offering_id: "class-a",
  cohort_id: "cohort-a",
  title: "کلاس مجاز",
  members: [{ person_id: "learner-a", member_type: "CANDIDATE" }],
  instructor_person_ids: [],
};

function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const result = render(
    <QueryClientProvider client={client}>
      <AdminAcademyOperationsWorkspace
        accessToken="test"
        organizationId="org-a"
        personId="admin-a"
      />
    </QueryClientProvider>,
  );
  return { ...result, client };
}

function sendResponse(path: string) {
  if (path === "/api/v1/admin/academy/cohorts") {
    return { data: { items: [cohort], next_offset: null } };
  }
  if (path === "/api/v1/admin/academy/cohorts/{cohort_id}/classes") {
    return { data: { cohort_id: "cohort-b", items: [classA], next_offset: null } };
  }
  return { error: "unexpected request" };
}

describe("Admin Academy stale-response isolation", () => {
  it("rejects a class page from another cohort before requesting any class detail", async () => {
    network.GET.mockImplementation(async (path: string) => sendResponse(path));
    const { client } = mount();

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "شناسه گروه فهرست کلاس‌ها تطبیق ندارد.",
      ),
    );
    expect(network.GET).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("کلاس مجاز")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "ثبت غایب" })).not.toBeInTheDocument();
    expect(network.POST).not.toHaveBeenCalled();
    client.clear();
  });

  it("does not request a report if the roster response belongs to a different class", async () => {
    network.GET.mockImplementation(async (path: string) => {
      if (path === "/api/v1/admin/academy/cohorts") {
        return { data: { items: [cohort], next_offset: null } };
      }
      if (path === "/api/v1/admin/academy/cohorts/{cohort_id}/classes") {
        return { data: { cohort_id: "cohort-a", items: [classA], next_offset: null } };
      }
      if (path === "/api/v1/class-offerings/{class_offering_id}/roster") {
        return { data: { ...rosterA, class_offering_id: "class-b" } };
      }
      if (path === "/api/v1/class-offerings/{class_offering_id}/sessions") {
        return { data: [] };
      }
      if (path === "/api/v1/class-offerings/{class_offering_id}/activity") {
        return { data: { class_offering_id: "class-a", items: [], is_truncated: false } };
      }
      return { error: "unexpected request" };
    });
    const { client } = mount();
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "فهرست افراد با کلاس و گروه انتخاب‌شده تطبیق ندارد.",
      ),
    );
    const visitedPaths = network.GET.mock.calls.map((call) => call[0] as string);
    expect(visitedPaths).not.toContain(
      "/api/v1/class-offerings/{class_offering_id}/report-cards/{person_id}",
    );
    expect(screen.queryByText("learner-a")).not.toBeInTheDocument();
    expect(network.POST).not.toHaveBeenCalled();
    client.clear();
  });

  it("blocks attendance access and display when a session response belongs to another class", async () => {
    network.GET.mockImplementation(async (path: string) => {
      if (path === "/api/v1/admin/academy/cohorts") {
        return { data: { items: [cohort], next_offset: null } };
      }
      if (path === "/api/v1/admin/academy/cohorts/{cohort_id}/classes") {
        return { data: { cohort_id: "cohort-a", items: [classA], next_offset: null } };
      }
      if (path === "/api/v1/class-offerings/{class_offering_id}/roster") {
        return { data: rosterA };
      }
      if (path === "/api/v1/class-offerings/{class_offering_id}/sessions") {
        return { data: [{
          session_id: "session-b", class_offering_id: "class-b",
          title: "جلسه غیرمجاز", starts_at: "2026-10-09T10:00:00Z",
          ends_at: "2026-10-09T11:00:00Z", delivery_mode: "IN_PERSON",
          status: "SCHEDULED",
        }] };
      }
      if (path === "/api/v1/class-offerings/{class_offering_id}/activity") {
        return { data: { class_offering_id: "class-a", items: [], is_truncated: false } };
      }
      if (path === "/api/v1/class-offerings/{class_offering_id}/report-cards/{person_id}") {
        return { data: {
          class_offering_id: "class-a", cohort_id: "cohort-a",
          person_id: "learner-a", attendance: [], subjects: [],
          attendance_scope: "CLASS_OFFERING",
        } };
      }
      return { error: "unexpected request" };
    });
    const { client } = mount();
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "جلسات با کلاس انتخاب‌شده تطبیق ندارند.",
      ),
    );
    expect(network.GET.mock.calls.map((call) => call[0])).not.toContain(
      "/api/v1/sessions/{session_id}/attendance",
    );
    expect(screen.queryByText("جلسه غیرمجاز")).not.toBeInTheDocument();
    expect(network.POST).not.toHaveBeenCalled();
    client.clear();
  });
});
