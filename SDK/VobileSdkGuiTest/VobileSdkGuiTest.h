// VobileSdkGuiTest.h : PROJECT_NAME Ӧ�ó������ͷ�ļ�
//

#pragma once

#ifndef __AFXWIN_H__
	#error "�ڰ������ļ�֮ǰ������stdafx.h�������� PCH �ļ�"
#endif

#include "resource.h"		// ������


// CVobileSdkGuiTestApp:
// �йش����ʵ�֣������ VobileSdkGuiTest.cpp
//

class CVobileSdkGuiTestApp : public CWinApp
{
public:
	CVobileSdkGuiTestApp();

// ��д
	public:
	virtual BOOL InitInstance();
// ʵ��

	DECLARE_MESSAGE_MAP()
};

extern CVobileSdkGuiTestApp theApp;