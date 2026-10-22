# 現場以外｜GitHub 新聞網站 + Decap CMS

這是可直接部署的新聞網站原始碼：首頁、文章頁、分類頁、圖片上傳、RSS、站點地圖與 `/admin/` Decap CMS 編輯後台。

## 快速上線（不需自行編輯 HTML）

1. 在 GitHub 建立**公開** repository，建議名稱 `newsroom`（也可以是 `<你的帳號>.github.io`）。
2. 解壓縮本專案，將**資料夾裡的全部檔案**（含 `.github` 隱藏資料夾）上傳到 repository 的 `main` 分支根目錄。可用 GitHub 網頁版 `Add file → Upload files`，注意 GitHub 網頁上傳隱藏檔可能不方便；推薦使用 GitHub Desktop 或 git。
3. GitHub repository → `Settings → Pages → Build and deployment → Source` 選 `GitHub Actions`。
4. 前往 `Actions` 頁籤檢查部署。網址一般是 `https://你的帳號.github.io/newsroom/`；若 repository 名為 `<你的帳號>.github.io`，則網址是 `https://你的帳號.github.io/`。
5. 網站已公開，但**此時 `/admin/` 還不能登入**。請繼續設定 OAuth。

## 啟用後台登入：不可略過

GitHub Pages 只有靜態託管，**不能自己處理 GitHub OAuth 的機密交換**。Decap CMS 使用 GitHub backend 時，必須搭配獨立的 OAuth 驗證代理（或改用提供驗證的其他主機服務）。本專案刻意**不放置任何假的登入功能，也不要求將 Client Secret 寫進公開儲存庫**。

推薦方式：參考 [Decap CMS GitHub backend](https://decapcms.org/docs/github-backend/) 與 [Cloudflare Worker OAuth proxy 範例](https://github.com/sterlingwes/decap-proxy)，部署你的 OAuth proxy，並在 GitHub 建立 OAuth App，將 `Client Secret` 只保存在 Cloudflare Worker 的 **Secrets** 中。OAuth App callback URL 要符合 OAuth proxy 提供的 `/callback` 路徑；確切路徑以你所選的 proxy 文件為準。**不要**將 GitHub OAuth Secret、access token 上傳到本專案或放入前端 JavaScript。

OAuth proxy 建好後，回到 GitHub repository → `Settings → Secrets and variables → Actions → Variables`，建立：

- `CMS_OAUTH_BASE_URL` = OAuth proxy 網址，例如 `https://auth.example.com`（**不是**公開新聞網站網址）
- （可選）`SITE_URL` = 自訂網域完整網址，例如 `https://news.example.com`，不要以 `/` 結尾；沒有自訂網域就不必填。

再到 `Actions → Build and deploy news website → Run workflow` 手動重建。完成後進入 `https://你的帳號.github.io/newsroom/admin/`，點 GitHub 登入。**登入者需要 repository 的寫入權限**。

在 `static/admin/index.html` 中載入的 Decap CMS 是前端管理介面；`admin/config.yml` 會在每次建置時由 `scripts/build.py` 自動產生，請改 GitHub Variables，**不要直接修改 dist/admin/config.yml**。

## 編輯新聞

登入 `/admin/` → 「新聞文章」→ 「新增文章」→ 填寫固定欄位 → 保存草稿 → 送審 → 發布。專案已開啟 `editorial_workflow`；它透過 GitHub 分支與 Pull Request 管理草稿和審稿，實際的發布權限由 GitHub repository 存取權決定。發布到 `main` 後 GitHub Actions 自動建置網站（部署可能需要幾分鐘）。

文章源檔放在 `content/posts/*.md`，採 YAML front matter + Markdown 格式；圖片放在 `static/assets/uploads/`。

**注意：** `date` 是文章日期，非排程器。設定未來時間**不會自動延後發布**。要定時上架需要增加排程 GitHub Action 或其他服務。

## 修改網站名稱、分類和視覺

- `site.yml`：站名、標語、分類（修改分類時，也須同步修改 `scripts/build.py` 內後台選單）
- `static/assets/style.css`：顏色、字型、間距與響應式版面
- `src/templates/`：首頁、文章頁、分類頁的 HTML 結構
- `content/posts/`：Markdown 文章

## 本機預覽

```bash
python -m pip install -r requirements.txt
GITHUB_REPOSITORY=yourname/newsroom python scripts/build.py
python -m http.server 8000 --directory dist
```

前往 http://localhost:8000/ 。注意：以 `newsroom` 專案路徑建置時，CSS 路徑會指向 `/newsroom/assets/...`，在本機伺服器根目錄測試時可能無法正確顯示樣式。**最簡單的本地完整預覽：** 在專案根目錄執行 `GITHUB_REPOSITORY=yourname/yourname.github.io python scripts/build.py` 產生 root-base 版，再啟動上述伺服器。正式部署仍會自動依 GitHub repository 判斷路徑。

## 已知限制與維護

- GitHub Pages 網站公開不等於後台授權開放。需要 OAuth proxy，且用戶必須有 GitHub repository 寫入權限。
- 站點是靜態產生：沒有讀者會員、留言、付費牆、全文搜尋、即時多人協同編輯。
- 媒體存 Git repo：適合中小規模圖片和文字，不建議放大量影片、超大圖片；大型媒體建議改外部圖庫或物件儲存。
- 修改已存在文章的檔名會改變網址。建議發布後固定檔名。
- 後台 `editorial_workflow` 的每次變更會觸發 GitHub 工作流程；若遇 PR 權限問題，可先切換至簡單發布模式，但需考慮權限控管。
