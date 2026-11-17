import os

import pytest

from final.src.runtime.artifacts import read_sandbox_file


def test_read_regular_sandbox_file_is_bounded(tmp_path):
    (tmp_path/'result').write_bytes(b'valid')
    assert read_sandbox_file(tmp_path,'result',max_bytes=5)==b'valid'
    with pytest.raises(ValueError,match='size'):
        read_sandbox_file(tmp_path,'result',max_bytes=4)


def test_file_symlink_does_not_leak_host_canary(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir()
    (tmp_path/'canary').write_text('secret fixture')
    (workspace/'result').symlink_to(tmp_path/'canary')
    with pytest.raises(ValueError,match='unsafe'):
        read_sandbox_file(workspace,'result')


def test_intermediate_symlink_does_not_leak_host_canary(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir()
    outside=tmp_path/'outside';outside.mkdir()
    (outside/'result').write_text('secret fixture')
    (workspace/'export').symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError,match='unsafe'):
        read_sandbox_file(workspace,'export/result')


@pytest.mark.parametrize('relative',['../canary','/etc/passwd',''])
def test_artifact_path_must_be_relative_and_nonempty(tmp_path,relative):
    with pytest.raises(ValueError):
        read_sandbox_file(tmp_path,relative)


def test_fifo_is_rejected_without_blocking(tmp_path):
    os.mkfifo(tmp_path/'fifo')
    with pytest.raises(ValueError,match='regular'):
        read_sandbox_file(tmp_path,'fifo')
