from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models import User
from tests.helpers import (
    bootstrap_coach,
    bootstrap_player_on_team,
    token_from_invite_link,
)


def _routine_body(team_id: str) -> dict:
    return {
        "name": "Recovery day",
        "description": "Light recovery work",
        "objective": "Reduce fatigue",
        "exercises": [
            {"name": "Light cycling", "duration_minutes": 10},
            {"name": "Stretching", "duration_minutes": 15},
        ],
        "duration_minutes": 25,
        "intensity": "low",
        "frequency": "as needed",
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=7)).isoformat(),
        "instructions": "Keep heart rate easy",
        "team_id": team_id,
    }


def test_team_routine_creates_assignment_per_player(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Routine FC",
        admin_email="routine-admin@example.com",
        coach_email="routine-coach@example.com",
    )
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "Routine Squad"},
    ).json()
    for email in ["routine-p1@example.com", "routine-p2@example.com"]:
        invite = client.post(
            f"/api/v1/teams/{team['id']}/players",
            headers=coach_headers,
            json={"name": email, "email": email},
        )
        assert invite.status_code == 200
        client.post(
            "/api/v1/auth/accept-invite",
            json={
                "token": token_from_invite_link(invite.json()["invite_link"]),
                "password": "playerpass1",
            },
        )

    created = client.post(
        "/api/v1/routines",
        headers=coach_headers,
        json=_routine_body(team["id"]),
    )
    assert created.status_code == 200
    assert created.json()["assignment_count"] == 2


def test_cannot_skip_not_started_to_completed(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Skip FC",
        admin_email="skip-admin@example.com",
        coach_email="skip-coach@example.com",
    )
    player_headers, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="Skip Squad",
        player_email="skip-player@example.com",
    )
    created = client.post(
        "/api/v1/routines",
        headers=coach_headers,
        json=_routine_body(team_id),
    )
    assert created.status_code == 200

    listed = client.get("/api/v1/routines", headers=player_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assignment_id = listed.json()[0]["id"]

    skipped = client.post(
        f"/api/v1/player/routines/{assignment_id}/status",
        headers=player_headers,
        json={"status": "completed"},
    )
    assert skipped.status_code == 422


def test_player_cannot_update_another_players_assignment(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="IsoRoutine FC",
        admin_email="isoroutine-admin@example.com",
        coach_email="isoroutine-coach@example.com",
    )
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "IsoRoutine Squad"},
    ).json()

    players: list[dict[str, str]] = []
    for email in ["isoroutine-a@example.com", "isoroutine-b@example.com"]:
        invite = client.post(
            f"/api/v1/teams/{team['id']}/players",
            headers=coach_headers,
            json={"name": email, "email": email},
        ).json()
        accepted = client.post(
            "/api/v1/auth/accept-invite",
            json={
                "token": token_from_invite_link(invite["invite_link"]),
                "password": "playerpass1",
            },
        )
        players.append(
            {"Authorization": f"Bearer {accepted.json()['access_token']}"}
        )

    created = client.post(
        "/api/v1/routines",
        headers=coach_headers,
        json=_routine_body(team["id"]),
    )
    assert created.status_code == 200

    a_list = client.get("/api/v1/routines", headers=players[0]).json()
    assignment_a = a_list[0]["id"]

    denied = client.post(
        f"/api/v1/player/routines/{assignment_a}/status",
        headers=players[1],
        json={"status": "in_progress"},
    )
    assert denied.status_code == 404


def test_player_targeted_routine_not_listed_to_unrelated_coach(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_a, org_id = bootstrap_coach(
        client,
        club_name="LeakRoutine FC",
        admin_email="leakroutine-admin@example.com",
        coach_email="leakroutine-coach-a@example.com",
    )
    admin_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "leakroutine-admin@example.com",
            "password": "clubadmin1",
        },
    )
    admin_headers = {
        "Authorization": f"Bearer {admin_login.json()['access_token']}"
    }
    coach_b_invite = client.post(
        f"/api/v1/organizations/{org_id}/coaches",
        headers=admin_headers,
        json={"name": "Other Coach", "email": "leakroutine-coach-b@example.com"},
    ).json()
    coach_b = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(coach_b_invite["invite_link"]),
            "password": "coachpass2",
        },
    )
    coach_b_headers = {
        "Authorization": f"Bearer {coach_b.json()['access_token']}"
    }

    player_headers, _, _ = bootstrap_player_on_team(
        client,
        coach_a,
        team_name="Coach A Only",
        player_email="leakroutine-player@example.com",
    )
    player_id = client.get("/api/v1/me", headers=player_headers).json()["id"]

    body = _routine_body("00000000-0000-0000-0000-000000000000")
    del body["team_id"]
    body["player_ids"] = [player_id]
    body["name"] = "Secret recovery"

    created = client.post("/api/v1/routines", headers=coach_a, json=body)
    assert created.status_code == 200
    routine_id = created.json()["id"]

    listed_a = client.get("/api/v1/routines", headers=coach_a)
    assert listed_a.status_code == 200
    assert any(r["id"] == routine_id for r in listed_a.json())

    listed_b = client.get("/api/v1/routines", headers=coach_b_headers)
    assert listed_b.status_code == 200
    assert all(r["id"] != routine_id for r in listed_b.json())


def test_dashboard_routine_counts_after_transitions(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="DashRoutine FC",
        admin_email="dashroutine-admin@example.com",
        coach_email="dashroutine-coach@example.com",
    )
    player_headers, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="DashRoutine Squad",
        player_email="dashroutine-player@example.com",
    )
    created = client.post(
        "/api/v1/routines",
        headers=coach_headers,
        json=_routine_body(team_id),
    )
    assert created.status_code == 200

    before = client.get(
        f"/api/v1/teams/{team_id}/dashboard",
        headers=coach_headers,
    )
    assert before.status_code == 200
    assert before.json()["routine_counts"] == {
        "assigned": 1,
        "in_progress": 0,
        "completed": 0,
    }

    assignment_id = client.get(
        "/api/v1/routines", headers=player_headers
    ).json()[0]["id"]

    progress = client.post(
        f"/api/v1/player/routines/{assignment_id}/status",
        headers=player_headers,
        json={"status": "in_progress"},
    )
    assert progress.status_code == 200

    mid = client.get(
        f"/api/v1/teams/{team_id}/dashboard",
        headers=coach_headers,
    ).json()["routine_counts"]
    assert mid == {"assigned": 1, "in_progress": 1, "completed": 0}

    done = client.post(
        f"/api/v1/player/routines/{assignment_id}/status",
        headers=player_headers,
        json={"status": "completed"},
    )
    assert done.status_code == 200

    after = client.get(
        f"/api/v1/teams/{team_id}/dashboard",
        headers=coach_headers,
    ).json()["routine_counts"]
    assert after == {"assigned": 1, "in_progress": 0, "completed": 1}
