from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from server.main import app

    return TestClient(app)


@pytest.mark.e2e
class TestFileUploadE2E:
    @patch("server.main.get_project_root")
    def test_upload_and_download_flow(self, mock_root, client, tmp_path):
        mock_root.return_value = str(tmp_path)
        from tests.test_auth import auth_header

        # 1. Upload a file
        file_content = b"E2E test content"
        file = ("e2e_test.txt", BytesIO(file_content), "text/plain")
        res = client.post(
            "/api/files/upload",
            files={"file": file},
            headers=auth_header(),
        )
        assert res.status_code == 200
        path = res.json()["path"]
        # 2. Download it back
        res = client.get(f"/api/files/download?path={path}", headers=auth_header())
        assert res.status_code == 200
        assert res.content == file_content
