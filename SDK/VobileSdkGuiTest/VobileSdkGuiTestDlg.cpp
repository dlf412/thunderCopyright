// VobileSdkGuiTestDlg.cpp : 实现文件
//

#include "stdafx.h"
#include "VobileSdkGuiTest.h"
#include "VobileSdkGuiTestDlg.h"
#include <vcri.h>
#include <utils.cpp>
#include <string>
#include <Windows.h>
using namespace std;

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

void vobile_sdk_callback(int32_t res_code, const char* str_url, const char* file_private_id);

// 用于应用程序“关于”菜单项的 CAboutDlg 对话框

class CAboutDlg : public CDialog
{
public:
	CAboutDlg();

	// 对话框数据
	enum { IDD = IDD_ABOUTBOX };

protected:
	virtual void DoDataExchange(CDataExchange* pDX);    // DDX/DDV 支持

	// 实现
protected:
	DECLARE_MESSAGE_MAP()
};

CAboutDlg::CAboutDlg() : CDialog(CAboutDlg::IDD)
{
}

void CAboutDlg::DoDataExchange(CDataExchange* pDX)
{
	CDialog::DoDataExchange(pDX);
}

BEGIN_MESSAGE_MAP(CAboutDlg, CDialog)
END_MESSAGE_MAP()


// CVobileSdkGuiTestDlg 对话框

CVobileSdkGuiTestDlg::CVobileSdkGuiTestDlg(CWnd* pParent /*=NULL*/)
	: CDialog(CVobileSdkGuiTestDlg::IDD, pParent)
{
	m_hIcon = AfxGetApp()->LoadIcon(IDR_MAINFRAME);
}

void CVobileSdkGuiTestDlg::DoDataExchange(CDataExchange* pDX)
{
    CDialog::DoDataExchange(pDX);
    DDX_Control(pDX, IDC_EDIT4, m_edit_url);
    DDX_Control(pDX, IDC_EDIT8, m_edit_vcri_result);
    DDX_Control(pDX, IDC_BTN_RESET, m_btn_reset);
    DDX_Control(pDX, IDC_EDIT11, m_edit_callback_result);
    DDX_Control(pDX, IDC_BTN_RESET2, m_btn_demo);
}

BEGIN_MESSAGE_MAP(CVobileSdkGuiTestDlg, CDialog)
	ON_WM_SYSCOMMAND()
	ON_WM_PAINT()
	ON_WM_QUERYDRAGICON()
	//}}AFX_MSG_MAP
	ON_BN_CLICKED(IDOK, &CVobileSdkGuiTestDlg::OnBnClickedOk)
	ON_BN_CLICKED(IDC_BUTTON1, &CVobileSdkGuiTestDlg::OnBnClickedButton1)
	ON_BN_CLICKED(IDCANCEL, &CVobileSdkGuiTestDlg::OnBnClickedCancel)
	ON_BN_CLICKED(IDC_BTN_RESET, &CVobileSdkGuiTestDlg::OnBnClickedBtnReset)
	ON_WM_CLOSE()
    ON_BN_CLICKED(IDC_BTN_RESET2, &CVobileSdkGuiTestDlg::OnBnClickedBtnReset2)
END_MESSAGE_MAP()

// CVobileSdkGuiTestDlg 消息处理程序

//scan func
void SP_THREAD_CALL scan_processing_urls(void *arg)
{
	if (NULL!=arg)
	{ 
		CVobileSdkGuiTestDlg* pdlg=(CVobileSdkGuiTestDlg*)arg;
		pdlg->processing_impl();
	}
}

BOOL CVobileSdkGuiTestDlg::OnInitDialog()
{	
	CDialog::OnInitDialog();

	// 将“关于...”菜单项添加到系统菜单中。

	// IDM_ABOUTBOX 必须在系统命令范围内。
	ASSERT((IDM_ABOUTBOX & 0xFFF0) == IDM_ABOUTBOX);
	ASSERT(IDM_ABOUTBOX < 0xF000);

	CMenu* pSysMenu = GetSystemMenu(FALSE);
	if (pSysMenu != NULL)
	{
		CString strAboutMenu;
		strAboutMenu.LoadString(IDS_ABOUTBOX);
		if (!strAboutMenu.IsEmpty())
		{
			pSysMenu->AppendMenu(MF_SEPARATOR);
			pSysMenu->AppendMenu(MF_STRING, IDM_ABOUTBOX, strAboutMenu);
		}
	}

	// 设置此对话框的图标。当应用程序主窗口不是对话框时，框架将自动
	//  执行此操作
	SetIcon(m_hIcon, TRUE);			// 设置大图标
	SetIcon(m_hIcon, FALSE);		// 设置小图标

	// TODO: 在此添加额外的初始化代码
    
	const char* vobile_user_agent = "thunder_client_v7.1.25";
	const char* vobile_client_id = "this-is-test-vobile-client-id";
	const char* vobile_api_key = "this-is-TMP-apikey";

	int code;
	code = vcri_init(NO_PROXY, NULL);
	if (code != 0)
	{
		MessageBox("init error", "error", MB_OK);
		return TRUE;
	}

	code = vcri_set_api_key(vobile_api_key);
	if (code != 0)
	{
		MessageBox("set api key error", "error", MB_OK);
		return TRUE;
	}

	code = vcri_set_client_id(vobile_client_id);
	if (code != 0)
	{
		MessageBox("set client id error", "error", MB_OK);
		return TRUE;
	}

	code = vcri_set_program_info(vobile_user_agent);
	if (code != 0)
	{
		MessageBox("set program info error", "error", MB_OK);
		return TRUE;
	}

	m_bScanRunning = true;
	ThreadCreate(scan_processing_urls,this);
    

	return TRUE;  // 除非将焦点设置到控件，否则返回 TRUE
}

void CVobileSdkGuiTestDlg::OnSysCommand(UINT nID, LPARAM lParam)
{
	if ((nID & 0xFFF0) == IDM_ABOUTBOX)
	{
		CAboutDlg dlgAbout;
		dlgAbout.DoModal();
	}
	else
	{
		CDialog::OnSysCommand(nID, lParam);
	}
}

// 如果向对话框添加最小化按钮，则需要下面的代码
//  来绘制该图标。对于使用文档/视图模型的 MFC 应用程序，
//  这将由框架自动完成。

void CVobileSdkGuiTestDlg::OnPaint()
{
	if (IsIconic())
	{
		CPaintDC dc(this); // 用于绘制的设备上下文

		SendMessage(WM_ICONERASEBKGND, reinterpret_cast<WPARAM>(dc.GetSafeHdc()), 0);

		// 使图标在工作区矩形中居中
		int cxIcon = GetSystemMetrics(SM_CXICON);
		int cyIcon = GetSystemMetrics(SM_CYICON);
		CRect rect;
		GetClientRect(&rect);
		int x = (rect.Width() - cxIcon + 1) / 2;
		int y = (rect.Height() - cyIcon + 1) / 2;

		// 绘制图标
		dc.DrawIcon(x, y, m_hIcon);
	}
	else
	{

		CDialog::OnPaint();
	}
}

//当用户拖动最小化窗口时系统调用此函数取得光标
//显示。
HCURSOR CVobileSdkGuiTestDlg::OnQueryDragIcon()
{
	return static_cast<HCURSOR>(m_hIcon);
}

void CVobileSdkGuiTestDlg::OnBnClickedButton1()
{
	CFileDialog *fileDialog; 
	fileDialog = new CFileDialog(
		TRUE,
		NULL,
		NULL,
		OFN_FILEMUSTEXIST | OFN_HIDEREADONLY,
		NULL
		);

	if(fileDialog->DoModal() == IDOK)
	{
		CString szGetName;
		szGetName = fileDialog->GetPathName();
	}

	delete fileDialog;
}

void CVobileSdkGuiTestDlg::clearInput()
{
	m_edit_url.SetWindowText("");
	m_edit_callback_result.SetWindowText("");
	m_edit_vcri_result.SetWindowText("");
}

void CVobileSdkGuiTestDlg::OnBnClickedCancel()
{
	OnCancel();
}

void CVobileSdkGuiTestDlg::OnBnClickedBtnReset()
{
	clearInput();
}

void CVobileSdkGuiTestDlg::OnClose()
{
	// TODO: 在此添加消息处理程序代码和/或调用默认值
	m_bScanRunning = false;
	vcri_fini();
	CDialog::OnClose();
}

int CVobileSdkGuiTestDlg::processing_impl()
{
	while(m_bScanRunning)
	{
		string  str_url;
		ThreadLock lock(m_deq_urls_lock);
		if (m_deq_urls.empty())
		{
			lock.Unlock();
			sp_sleep(500);
			continue;
		}

		str_url = m_deq_urls.front();
		m_deq_urls.pop_front();
		lock.Unlock();

		vcri_params_t params;
		memset(&params,0,sizeof(params));

		const char* file_name = "变形金刚4";
		string encode_name = encode_utf8((string)file_name);
		params.file_name = encode_name.c_str();

		CString url;
		m_edit_url.GetWindowText(url);
		url = url.Trim();
		string encoded_url = encode_utf8((string)url.GetBuffer());
		params.url = encoded_url.c_str();

		make_params(params);
		int res_code = vcri_identify(vobile_sdk_callback, &params);
	}

	return 0;
}

void CVobileSdkGuiTestDlg::OnBnClickedOk()
{
	CString url;
	m_edit_url.GetWindowText(url);
	url = url.Trim();

	if (url == "")
	{
		MessageBox("Please input a URL address!", "Tip", MB_OK);
		return;
	}

	vcri_params_t params;
	memset(&params,0, sizeof(params));

	const char* file_name = "变形金刚4";
	string encode_name = encode_utf8((string)file_name);
	params.file_name = encode_name.c_str();

	string encoded_url = encode_utf8((string)url.GetBuffer());
	params.url = encoded_url.c_str();

	make_params(params);
	int res_code = vcri_identify(vobile_sdk_callback, &params);

	CString result_info;
	result_info.Format("%d", res_code);
	m_edit_vcri_result.SetWindowText(result_info);
}

void CVobileSdkGuiTestDlg::make_params(vcri_params_t& params)
{
	params.file_private_id = "THIS-IS-A-TEST-PRIVATE-ID";
	params.file_size = 12345678;
	params.mime_type = "video/mp4";
	params.referer = "http://www.dytt8.net";

	params.struct_version = 1;
	params.struct_size = sizeof(params);
}

void vobile_sdk_callback(int32_t res_code, const char* str_url, const char* file_private_id)
{
	CVobileSdkGuiTestDlg* pDlg = (CVobileSdkGuiTestDlg*)(AfxGetMainWnd());
	if(!pDlg)
	{
		return;
	}

	CString result_info;
	if (res_code == INFRINGING)
	{
		result_info.Format("%s","Infringing");
	}
	else if (res_code == NON_INFRINGING)
	{
		result_info.Format("%s","Non-infringing");
	}
	else if (res_code == CANNOT_IDENTIFY)
	{
		result_info.Format("%s","Cannot-identify");
	}
	else
	{
		result_info.Format("%s", "Processing");
		ThreadLock my_lock(pDlg->m_deq_urls_lock);
		pDlg->m_deq_urls.push_back(str_url);
	}

	pDlg->m_edit_callback_result.SetWindowText(result_info);
}
void CVobileSdkGuiTestDlg::OnBnClickedBtnReset2()
{
    // TODO: 在此添加控件通知处理程序代码
    const char* vobile_user_agent = "thunder_client_v7.1.25";
    const char* vobile_client_id = "this-is-test-vobile-client-id";
    const char* vobile_api_key = "this-is-TMP-apikey";

    int code;
    code = vcri_init(SYSTEM_PROXY, NULL);
    if (code != 0)
    {
        MessageBox("init error", "error", MB_OK);
        return ;
    }

    code = vcri_set_api_key(vobile_api_key);
    if (code != 0)
    {
        MessageBox("set api key error", "error", MB_OK);
        return ;
    }

    code = vcri_set_client_id(vobile_client_id);
    if (code != 0)
    {
        MessageBox("set client id error", "error", MB_OK);
        return ;
    }

    code = vcri_set_program_info(vobile_user_agent);
    if (code != 0)
    {
        MessageBox("set program info error", "error", MB_OK);
        return ;
    }

    vcri_params_t params;
    memset(&params,0, sizeof(params));

    params.file_private_id = "sample-private-id";
    params.file_size = 1234567890;
    params.mime_type = "video/mp4";
    params.referer = "http://host/sample.html";
    params.struct_version = 1;
    params.struct_size = sizeof(params);

    const char* file_name = "sample.mp4";
    string encode_name = encode_utf8((string)file_name);
    params.file_name = encode_name.c_str();
    //params.file_name = "sample.mp4";

    string encoded_url = encode_utf8((string)"http://host/sample.mp4");
    params.url = encoded_url.c_str();
    //params.url = "http://host/sample.mp4";

    int res_code = vcri_identify(vobile_sdk_callback, &params);
    vcri_fini();

    CString result_info;
    result_info.Format("%d", res_code);
    m_edit_vcri_result.SetWindowText(result_info);
}

bool CVobileSdkGuiTestDlg::Init()
{
    
 return 1;
}
