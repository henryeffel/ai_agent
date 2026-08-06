import argparse

from ieum.config import get_settings
from ieum.database import get_session_factory
from ieum.demo.maintenance import DemoMaintenanceService
from ieum.providers.vector_search import get_vector_search_provider


def main():
    parser = argparse.ArgumentParser(description="IEUM public demo maintenance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed", help="Upsert bundled demo knowledge")
    cleanup = subparsers.add_parser("cleanup", help="Delete expired demo plans")
    cleanup.add_argument("--older-than-hours", type=int, default=24)
    cleanup.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    if get_settings().app_mode != "demo":
        parser.error("이 명령은 APP_MODE=demo에서만 실행할 수 있습니다.")
    if args.command == "cleanup" and not args.confirm:
        parser.error("cleanup에는 데이터 삭제 확인을 위한 --confirm이 필요합니다.")
    if args.command == "seed":
        service = DemoMaintenanceService(
            get_vector_search_provider(),
            get_session_factory(),
        )
        print(f"seeded_chunks={service.seed_knowledge()}")
        return
    service = DemoMaintenanceService(None, get_session_factory())
    print(
        "deleted_demo_plans="
        f"{service.cleanup_plans(older_than_hours=args.older_than_hours)}"
    )


if __name__ == "__main__":
    main()
