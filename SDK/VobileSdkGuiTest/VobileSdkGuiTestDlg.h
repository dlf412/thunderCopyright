// VobileSdkGuiTestDlg.h : ͷ�ļ�
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

// CVobileSdkGuiTestDlg �Ի���
class CVobileSdkGuiTestDlg : public CDialog
{
// ����
public:
	CVobileSdkGuiTestDlg(CWnd* pParent = NULL);	// ��׼���캯��

// �Ի�������
	enum { IDD = IDD_VOBILESDKGUITEST_DIALOG };

	protected:
	virtual void DoDataExchange(CDataExchange* pDX);	// DDX/DDV ֧��


// ʵ��
protected:
	HICON m_hIcon;

	// ���ɵ���Ϣӳ�亯��
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
