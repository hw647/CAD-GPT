from flask import Flask, request, jsonify, render_template, send_from_directory
import google.generativeai as genai
import os

app = Flask(__name__, template_folder='templates')

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

local_db = {
    "cmd": {
        "원 그리기": "명령어: CIRCLE / 단축키: C\n\n사용법:\n1. C 입력 후 Enter\n2. 중심점 클릭\n3. 반지름 입력 후 Enter\n\n팁: Shift+우클릭으로 중심점 스냅 활용하면 더 정확해요.",
        "선 긋기": "명령어: LINE / 단축키: L\n\n사용법:\n1. L 입력 후 Enter\n2. 시작점 클릭\n3. 끝점 클릭\n4. Enter로 종료\n\n팁: F8(직교모드)을 켜면 수평/수직선만 그을 수 있어요.",
        "사각형 그리기": "명령어: RECTANG / 단축키: REC\n\n사용법:\n1. REC 입력 후 Enter\n2. 첫 번째 꼭짓점 클릭\n3. 반대편 꼭짓점 클릭\n\n팁: @가로,세로 형식으로 정확한 크기 입력 가능. 예: @100,50",
        "레이어 추가": "명령어: LAYER / 단축키: LA\n\n사용법:\n1. LA 입력 후 Enter\n2. 레이어 관리자 창 열림\n3. 새 레이어 버튼(+) 클릭\n4. 이름 입력 후 Enter\n\n팁: 레이어마다 색상 지정하면 도면 구분이 쉬워요.",
        "치수선 넣기": "명령어: DIMLINEAR / 단축키: DLI\n\n사용법:\n1. DLI 입력 후 Enter\n2. 첫 번째 치수 기준점 클릭\n3. 두 번째 점 클릭\n4. 치수선 위치 클릭\n\n팁: 경사진 선의 치수는 DIMALIGNED(DAL) 사용.",
        "복사하기": "명령어: COPY / 단축키: CO\n\n사용법:\n1. CO 입력 후 Enter\n2. 복사할 객체 선택 후 Enter\n3. 기준점 클릭\n4. 붙여넣을 위치 클릭\n\n팁: 여러 곳에 복사하려면 위치를 계속 클릭하면 돼요.",
        "이동하기": "명령어: MOVE / 단축키: M\n\n사용법:\n1. M 입력 후 Enter\n2. 이동할 객체 선택 후 Enter\n3. 기준점 클릭\n4. 이동할 위치 클릭\n\n팁: 정확한 거리로 이동하려면 @X,Y 형식으로 입력.",
        "삭제하기": "명령어: ERASE / 단축키: E\n\n사용법:\n1. E 입력 후 Enter\n2. 삭제할 객체 선택\n3. Enter\n\n팁: 실수로 지웠다면 Ctrl+Z로 바로 되돌릴 수 있어요.",
        "객체 자르기": "명령어: TRIM / 단축키: TR\n\n사용법:\n1. TR 입력 후 Enter 두 번\n2. 자를 부분 클릭\n\n팁: Enter 두 번 누르면 전체 선택 모드로 바로 자르기 가능.",
    },
    "err": {
        "치수 글자 안보임": "원인: 도면 크기에 비해 치수 문자 크기가 너무 작음\n\n해결:\n1. D 입력 후 Enter (DIMSTYLE)\n2. 수정 클릭\n3. 맞춤 탭 -> 전체 축척 사용 값을 키워줍니다.",
        "마우스 뚝뚝 끊김": "원인: 스냅(SNAP) 모드가 켜져 있음\n\n해결:\n1. 기능키 F9를 눌러 스냅을 끕니다.\n2. 또는 하단 상태바에서 스냅 버튼 클릭하여 끄기.",
        "마우스 휠 줌 속도": "원인: 휠 확대 비율 설정이 낮음\n\n해결:\n1. ZOOMFACTOR 명령어 입력\n2. 값을 100으로 올립니다. (기본값: 60)",
        "Fatal Error": "원인: 도면 데이터 손상\n\n해결:\n1. RECOVER 명령어로 도면 복구 시도\n2. .sv$ 자동저장 파일을 .dwg로 변경 후 열기\n3. 마지막 저장 버전으로 복구.",
        "Cannot open file": "원인: 파일 경로에 한글/특수문자 또는 파일 손상\n\n해결:\n1. 파일 경로를 영문으로 변경\n2. 다른 버전의 AutoCAD로 열어보기\n3. 백업 파일(.bak)을 .dwg로 변경 후 열기.",
        "Layer is locked": "원인: 현재 레이어가 잠금 상태\n\n해결:\n1. LA 입력 -> 레이어 관리자 열기\n2. 해당 레이어의 자물쇠 아이콘 클릭하여 잠금 해제\n3. 다른 레이어로 전환 후 작업.",
    }
}

prompts = {
    "cmd": "당신은 AutoCAD 전문가입니다. 명령어와 사용법을 [명령어/단축키], [단계별 사용법], [팁] 구조로 한국어로 답변하세요.",
    "err": "당신은 AutoCAD 오류 해결 전문가입니다. [원인], [해결 방법] 구조로 한국어로 답변하세요."
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    query = data.get("query", "").strip()
    tab = data.get("tab", "cmd")

    if not query:
        return jsonify({"answer": "질문을 입력해주세요.", "source": "error"})

    for key, val in local_db[tab].items():
        if query.lower() in key.lower() or key.lower() in query.lower():
            return jsonify({"answer": val, "source": "local"})

    if not GEMINI_API_KEY:
        return jsonify({"answer": "API 키가 설정되지 않았어요.", "source": "error"})

    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest",
            system_instruction=prompts[tab]
        )
        response = model.generate_content(query)
        return jsonify({"answer": response.text, "source": "ai"})
    except Exception as e:
        return jsonify({"answer": f"AI 오류: {str(e)}", "source": "error"})

@app.route("/db", methods=["GET"])
def get_db():
    tab = request.args.get("tab", "cmd")
    return jsonify({"keys": list(local_db[tab].keys())})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
