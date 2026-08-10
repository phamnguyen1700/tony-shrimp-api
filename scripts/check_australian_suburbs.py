import asyncio

from app.services.user import check_address_locality, suggest_address_suburbs


async def main() -> None:
    search = input("Search suburb/postcode [Melbourne Airport]: ").strip()
    if not search:
        search = "Waratah"

    result = await suggest_address_suburbs(search)
    print("Suggestions:")
    print(result.model_dump())
    print()

    postcode = input("Postcode check [3045]: ").strip() or "7321"
    suburb = input("Suburb check [Melbourne Airport]: ").strip()
    if not suburb:
        suburb = "Waratah"

    check_result = await check_address_locality(
        postcode=postcode,
        suburb=suburb,
    )
    print("Locality check:")
    print(check_result.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
