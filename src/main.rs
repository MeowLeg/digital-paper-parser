use base64::Engine as _;
use pdf2image::{
    DPI, Pages, PDF, PDF2ImageError, RenderOptions,
    image::ImageFormat,
};
use reqwest::header;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::info;
use std::io::{Read, Seek, SeekFrom};
use std::io::Cursor;

// ======================== 自定义错误类型（无冗余） ========================
#[derive(Error, Debug)]
pub enum PdfKimiError {
    /// 直接包装pdf2image官方错误
    #[error("PDF转换错误: {0}")]
    Pdf2Image(#[from] PDF2ImageError),
    #[error("IO错误: {0}")]
    Io(#[from] std::io::Error),
    #[error("HTTP请求错误: {0}")]
    Reqwest(#[from] reqwest::Error),
    #[error("JSON序列化/反序列化错误: {0}")]
    SerdeJson(#[from] serde_json::Error),
    #[error("图像处理错误: {0}")]
    Image(#[from] image::ImageError),
    #[error("HTTP头配置错误: {0}")]
    HeaderError(#[from] reqwest::header::InvalidHeaderValue),
    #[error("Kimi API响应错误: {0}")]
    ApiResponse(String),
    #[error("PDF无有效页面内容")]
    PdfNoPages,
    #[error("Kimi API未返回任何结果")]
    NoApiResult,
}

// ======================== 业务数据结构（与原Python完全一致） ========================
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Article {
    pub title: String,
    pub author: String,
    pub collaborator: String,
    pub photo: String,
    pub content: String,
    pub next_page: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ParseResponse {
    pub success: bool,
    #[serde(rename = "errMsg")]
    pub err_msg: String,
    pub data: Vec<Article>,
}

// ======================== Kimi API 调用结构体（无变化） ========================
#[derive(Debug, Serialize)]
#[serde(rename_all = "snake_case")]
enum MessageRole {
    System,
    User,
    Assistant,
}

#[derive(Debug, Serialize)]
struct ChatMessage {
    role: MessageRole,
    content: serde_json::Value,
}

#[derive(Debug, Serialize)]
struct ChatCompletionRequest {
    model: String,
    messages: Vec<ChatMessage>,
    response_format: ResponseFormat,
}

#[derive(Debug, Serialize)]
struct ResponseFormat {
    r#type: String,
}

#[derive(Debug, Deserialize)]
struct ChatCompletionResponse {
    choices: Vec<Choice>,
}

#[derive(Debug, Deserialize)]
struct Choice {
    message: ChoiceMessage,
}

#[derive(Debug, Deserialize)]
struct ChoiceMessage {
    content: String,
}

// ======================== 核心解析器（100%匹配官方API） ========================
pub struct PdfKimiParser {
    api_key: String,
    http_client: reqwest::Client,
}

impl PdfKimiParser {
    /// 创建解析器实例（无变化）
    pub fn new(api_key: &str) -> Self {
        let http_client = reqwest::Client::builder()
            .no_proxy()
            .danger_accept_invalid_hostnames(true)
            .danger_accept_invalid_certs(true)
            .timeout(std::time::Duration::from_secs(600))
            .build()
            .expect("HTTP客户端初始化失败，请检查网络环境");

        Self {
            api_key: api_key.to_string(),
            http_client,
        }
    }

    /// PDF单页转Base64（核心修复：无非法字段 + Seek trait + 类型匹配）
    pub fn pdf_single_page_to_base64(&self, pdf_path: &str, page_num: u32) -> Result<String, PdfKimiError> {
        info!("开始转换PDF：{} 第{}页（300DPI高清）", pdf_path, page_num);

        // 1. 创建PDF实例（官方API）
        let pdf = PDF::from_file(pdf_path)?;

        // 2. 配置渲染参数（严格匹配官方文档，无任何非法字段）
        let render_opts = RenderOptions {
            resolution: DPI::Uniform(300),  // 官方字段：分辨率
            scale: None,                    // 官方字段：缩放（None=不缩放）
            greyscale: false,               // 官方字段：关闭灰度
            crop: None,                     // 官方字段：无裁剪
            password: None,                 // 官方字段：无密码
            pdftocairo: false,              // 官方字段：使用默认pdftoppm渲染
        };

        // 3. 官方API渲染：得到DynamicImage
        let pages  = pdf.render(Pages::Single(page_num), render_opts)?;
        
        // 4. 检查是否有有效页面
        if pages.is_empty() {
            return Err(PdfKimiError::PdfNoPages);
        }
        let page_image = &pages[0];

        // 5. 核心修复：用Cursor创建可Seek的内存缓冲区
        let mut cursor = Cursor::new(Vec::new());
        
        // 6. 将图片写入Cursor（使用image::ImageOutputFormat，类型完全匹配）
        match page_image.write_to(&mut cursor, ImageFormat::Jpeg) {
            Ok(_) => {}
            Err(e) => {
                println!("图片处理错误（适配错误）：{}", e);
                return Err(PdfKimiError::ApiResponse("图片处理错误（适配错误）".into()))
            },
        }
        
        // 7. 重置Cursor指针到开头，准备读取内容
        cursor.seek(SeekFrom::Start(0))?;
        
        // 8. 读取Cursor中的内容到Vec<u8>（最终用于Base64编码）
        let mut img_buffer = Vec::new();
        cursor.read_to_end(&mut img_buffer)?;

        // 9. 检查内容有效性
        if img_buffer.is_empty() {
            return Err(PdfKimiError::PdfNoPages);
        }

        // 10. Base64编码（与原Python逻辑一致）
        let base64_str = base64::engine::general_purpose::STANDARD.encode(&img_buffer);
        info!("PDF转Base64成功，编码长度：{} 字符", base64_str.len());

        Ok(base64_str)
    }

    /// 调用Kimi API解析图片内容（无变化）
    pub async fn parse_with_kimi(&self, img_base64: &str) -> Result<ParseResponse, PdfKimiError> {
        info!("开始调用Kimi API（kimi-k2.5）解析电子报内容");

        let messages = vec![
            ChatMessage {
                role: MessageRole::System,
                content: serde_json::json!([
                    {
                        "type": "text",
                        "text": "电子报内容识别"
                    },
                    {
                        "type": "text",
                        "text": r#"json格式为：{
                            "success": true,
                            "errMsg": "识别成功",
                            "data": [
                                {
                                    "title": "文章标题",
                                    "author": "作者",
                                    "collaborator": "通讯员",
                                    "photo": "摄影",
                                    "content": "内容",
                                    "next_page": ""
                                }
                            ]
                        "#
                    }
                ]),
            },
            ChatMessage {
                role: MessageRole::User,
                content: serde_json::json!([
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": format!("data:image/png;base64,{}", img_base64)
                        }
                    },
                    {
                        "type": "text",
                        "text": "请完整且准确地识别电子报中的文章的内容和标点符号，以json列表的形式返回出来，列表内的对象包括文章名、作者、通讯员、摄影、内容等"
                    }
                ]),
            },
            ChatMessage {
                role: MessageRole::Assistant,
                content: serde_json::json!([
                    {
                        "type": "text",
                        "text": "干览镇应改为干𬒗镇"
                    },
                    {
                        "type": "text",
                        "text": "如文章末尾有“下紧转第x版”的，在返回的json中，next_page字段填写下一页的版面号，且content中不包含“下紧转第x版”"
                    },
                    {
                        "type": "text",
                        "text": "去掉内容开头“上紧接第x版”"
                    }
                ]),
            },
        ];

        let request_body = ChatCompletionRequest {
            model: "kimi-k2.5".to_string(),
            messages,
            response_format: ResponseFormat {
                r#type: "json_object".to_string(),
            },
        };
        // println!("body: {:?}", &request_body);

        let mut headers = header::HeaderMap::new();
        headers.insert(
            "Authorization",
            header::HeaderValue::from_str(&format!("Bearer {}", self.api_key))?,
        );
        headers.insert(
            "Content-Type",
            header::HeaderValue::from_str("application/json")?,
        );

        let response = self
            .http_client
            .post("https://api.moonshot.cn/v1/chat/completions")
            .headers(headers)
            .json(&request_body)
            .send()
            .await?;

        if !response.status().is_success() {
            let err_text = response.text().await?;
            return Err(PdfKimiError::ApiResponse(format!(
                "API请求失败 [状态码: {}]：{}",
                200,
                err_text
            )));
        }

        let chat_resp: ChatCompletionResponse = response.json().await?;
        let choice = chat_resp
            .choices
            .into_iter()
            .next()
            .ok_or(PdfKimiError::NoApiResult)?;
        
        let parse_resp: ParseResponse = serde_json::from_str(&choice.message.content)?;
        info!("Kimi API解析成功，共识别 {} 篇文章", parse_resp.data.len());

        Ok(parse_resp)
    }

    /// 多页PDF内容合并（无变化）
    pub async fn merge_multi_page_content(
        &self,
        mut main_resp: ParseResponse,
        next_pdf_paths: &[(&str, u32)],
    ) -> Result<ParseResponse, PdfKimiError> {
        if !main_resp.success {
            info!("主页面解析失败，无需合并多页内容");
            return Ok(main_resp);
        }

        info!("开始合并多页PDF内容，待处理文件数：{}", next_pdf_paths.len());

        for (pdf_path, page_num) in next_pdf_paths {
            let next_base64 = self.pdf_single_page_to_base64(pdf_path, *page_num)?;
            let next_resp = self.parse_with_kimi(&next_base64).await?;

            if next_resp.success {
                for main_article in &mut main_resp.data {
                    if !main_article.next_page.is_empty() {
                        for next_article in &next_resp.data {
                            if main_article.title.contains(&next_article.title) 
                                || next_article.title.contains(&main_article.title)
                            {
                                main_article.content.push_str(&next_article.content);
                                info!("成功合并文章【{}】的后续内容", main_article.title);
                            }
                        }
                    }
                }
            }
        }

        Ok(main_resp)
    }
}

// ======================== 主函数（无变化） ========================
#[tokio::main]
async fn main() -> Result<(), PdfKimiError> {
    // 初始化日志
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    // 配置参数（替换为你的实际值）
    let api_key = "sk-BSvteGexprXexqyk6O5RBSPJtcmBNzoZwHVnVAAmJTUPIZTE";
    let main_pdf_path = "resource/special/b2026-01-25_01.pdf";
    let next_pdf_paths = &[("resource/special/b2026-01-25_04.pdf", 1)];

    // 执行核心流程
    let parser = PdfKimiParser::new(api_key);
    let main_base64 = parser.pdf_single_page_to_base64(main_pdf_path, 1)?;
    let mut parse_result = parser.parse_with_kimi(&main_base64).await?;
    parse_result = parser.merge_multi_page_content(parse_result, next_pdf_paths).await?;

    // 打印结果
    let result_json = serde_json::to_string_pretty(&parse_result)?;
    println!("==================== 电子报解析最终结果 ====================\n{}", result_json);

    Ok(())
}