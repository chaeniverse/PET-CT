#!/bin/bash
# 외장하드 PET-CT 폴더들을 가명(C001…)으로 워크스테이션에 복사한다. 중간에 끊기면 다시 돌리면 이어서 한다.
# 가명 대응표·로그는 외장하드에만 쓴다. 화면·로그에는 가명만 나온다.
#
# 맥에서 실행한다(가이드 §6-1b). 원본은 읽기만 한다.
#   cp scripts/copy_cohort_dicom.sh ~/petct_copy.sh
#   nohup caffeinate -ims bash ~/petct_copy.sh > /dev/null 2>&1 &
#   tail -f /Volumes/EXTERNAL/PETCT_transfer_log.txt
# 연구실 내부망이면 WS 를 chlee@192.168.0.251 로 바꾸면 더 빠르다. 키 로그인(ssh-copy-id)이 먼저 되어 있어야 한다.
SRC="/Volumes/EXTERNAL/PET-CT"
MAP="/Volumes/EXTERNAL/PETCT_pseudonym_map.tsv"
LOG="/Volumes/EXTERNAL/PETCT_transfer_log.txt"
ERR="/Volumes/EXTERNAL/PETCT_transfer_errors.txt"
WS="chlee@pipet-cmccpt"
DEST="autopet3/dicom"
SSH_OPTS="-o BatchMode=yes -o ServerAliveInterval=60 -o ServerAliveCountMax=10 -o ControlMaster=auto -o ControlPath=$HOME/.ssh/cm-%r@%h:%p -o ControlPersist=10m"

# 1) 대응표: 처음 한 번만 만든다(폴더명 정렬 순서). 이미 있으면 그대로 써서 번호가 바뀌지 않게 한다
if [ ! -f "$MAP" ]; then
  find "$SRC" -mindepth 1 -maxdepth 1 -type d ! -name '.*' | LC_ALL=C sort | awk -F/ '{printf "C%03d\t%s\n", NR, $NF}' > "$MAP"
fi
echo "$(date '+%m-%d %H:%M') 시작: $(wc -l < "$MAP" | tr -d ' ')명" >> "$LOG"
ssh $SSH_OPTS "$WS" "mkdir -p $DEST" < /dev/null || { echo "워크스테이션 접속 실패(키 로그인 확인)"; exit 1; }

# 2) 환자별 복사 → 장수 확인 → 로그(가명·숫자만)
while IFS=$'\t' read -r id name; do
  n_src=$(find "$SRC/$name" -type f ! -name '.*' | wc -l | tr -d ' ')
  rsync -a --exclude '.DS_Store' --exclude '._*' -e "ssh $SSH_OPTS" "$SRC/$name/" "${WS}:$DEST/$id/" < /dev/null 2>> "$ERR"
  rc=$?
  n_dst=$(ssh $SSH_OPTS "$WS" "find $DEST/$id -type f | wc -l" < /dev/null | tr -d ' ')
  echo "$(date '+%m-%d %H:%M') $id rsync=$rc src=$n_src dst=$n_dst" >> "$LOG"
done < "$MAP"
echo "$(date '+%m-%d %H:%M') 끝" >> "$LOG"
