// VobileSdkGuiTestDlg.h : 头文件
//

#pragma once
#include "afxwin.h"
#include <iostream>
#include <string>
#include <vector>
#include <deque>
#include "afxcmn.h"
#include "thread.h"
#include <vcri.h>
using namespace std;

// CVobileSdkGuiTestDlg 对话框
class CVobileSdkGuiTestDlg : public CDialog
{
// 构造
public:
	CVobileSdkGuiTestDlg(CWnd* pParent = NULL);	// 标准构造函数

// 对话框数据
	enum { IDD = IDD_VOBILESDKGUITEST_DIALOG };

	protected:
	virtual void DoDataExchange(CDataExchange* pDX);	// DDX/DDV 支持


// 实现
protected:
	HICON m_hIcon;

	// 生成的消息映射函数
	virtual BOOL OnInitDialog();
	afx_msg void OnSysCommand(UINT nID, LPARAM lParam);
	afx_msg void OnPaint();
	afx_msg HCURSOR OnQueryDragIcon();
	DECLARE_MESSAGE_MAP()
public:
	afx_msg void OnBnClickedOk();
	CEdit m_edit_url;
	CEdit m_edit_vcri_result;
	CEdit m_edit_callback_result;
	CButton m_btn_reset;

	afx_msg void OnClose();
	afx_msg void OnBnClickedButton1();
	afx_msg void OnBnClickedCancel();
	afx_msg void OnBnClickedBtnReset();

	CriSection m_deq_urls_lock;
	deque<string> m_deq_urls;

	bool m_bScanRunning;
	void clearInput();
	int processing_impl();
	void make_params(vcri_params_t& params);
    CButton m_btn_demo;
    afx_msg void OnBnClickedBtnReset2();
    bool Init();


};
