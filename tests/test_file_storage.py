import os


class TestFileStorage:
    def test_save_file_creates_directory(self, tmp_path):
        from server.file_storage import save_file

        content = b"hello world"
        result = save_file(content, "user-abc", "test.txt", str(tmp_path))
        full_path = tmp_path / result
        assert os.path.exists(full_path)
        with open(full_path, "rb") as f:
            assert f.read() == content

    def test_save_file_returns_relative_path(self, tmp_path):
        from server.file_storage import save_file

        result = save_file(b"test", "user-abc", "file.txt", str(tmp_path))
        assert result == "user-abc/file.txt"

    def test_get_file_path_constructs_full_path(self, tmp_path):
        from server.file_storage import get_file_path

        path = get_file_path("user-abc/file.txt", str(tmp_path))
        assert str(path) == str(tmp_path / "user-abc" / "file.txt")