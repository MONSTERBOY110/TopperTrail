import httpx

from toppertrail.fetch.images import LiveImageReader, ReplayImageReader


def test_live_image_reader_runs_ocr_and_hashes():
    def handler(request):
        if request.url.path == "/a.png":
            return httpx.Response(200, headers={"content-type": "image/png"}, content=b"PNGDATA")
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html></html>")

    reader = LiveImageReader(
        ocr=lambda data: "AIR 1 ANUJ AGNIHOTRI" if data == b"PNGDATA" else "",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    it = reader.read("https://img.test/a.png")
    assert it.text == "AIR 1 ANUJ AGNIHOTRI" and it.image_sha256 and it.error is None
    assert reader.read("https://img.test/page").error == "not_image"


def test_replay_image_missing(tmp_path):
    assert ReplayImageReader(tmp_path).read("https://img.test/a.png").error == "missing_fixture"
