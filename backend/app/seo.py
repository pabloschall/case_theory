from xml.etree import ElementTree

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.cases.models import Case
from app.config.settings import get_settings
from app.db.session import get_db

router = APIRouter(tags=["seo"])
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
ElementTree.register_namespace("", SITEMAP_NAMESPACE)


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap(db: AsyncSession = Depends(get_db)) -> Response:
    origin = get_settings().public_site_url.rstrip("/")
    root = ElementTree.Element(f"{{{SITEMAP_NAMESPACE}}}urlset")

    def add_url(path: str, last_modified: str | None = None) -> None:
        entry = ElementTree.SubElement(root, f"{{{SITEMAP_NAMESPACE}}}url")
        ElementTree.SubElement(entry, f"{{{SITEMAP_NAMESPACE}}}loc").text = f"{origin}{path}"
        if last_modified:
            ElementTree.SubElement(entry, f"{{{SITEMAP_NAMESPACE}}}lastmod").text = last_modified

    add_url("/cases")
    result = await db.execute(
        select(Case.id, Case.updated_at)
        .where(Case.privacy == "public")
        .order_by(Case.updated_at.desc())
        .limit(49999)
    )
    for case_id, updated_at in result:
        add_url(f"/cases/{case_id}", updated_at.date().isoformat())

    return Response(
        content=ElementTree.tostring(root, encoding="utf-8", xml_declaration=True),
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )
