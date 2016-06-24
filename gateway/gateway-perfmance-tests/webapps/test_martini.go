package main

// Created at: [2014-06-28 13:04]

/* ============================================================================
   Requirements
   ------------
   + https support (https://)
   + secure websocket (wss://)
   + Performance test >> http://ziutek.github.io/web_bench/
      - siege -c 200 -t 20s http://ADDRESS:PORT/Hello/100
 * ==========================================================================*/


import (
	"log"
	"fmt"
	"flag"
	"time"
	"net/http"
	"runtime"
	"github.com/go-martini/martini"
// 	"github.com/martini-contrib/auth"
)


var m *martini.Martini
const AuthUser = "user"
const AuthPasswd = "passwd"

func index() (int, string) {
	time.Sleep(200 * time.Millisecond)
	return 200, "This is index."
}

var (
	port_flag = flag.Int("port", 9002, "Bind port")
	port int
	size_flag = flag.Int("size", 4, "GOMAXPROCS size")
	size int
)

func init() {
	flag.Parse()
	port = *port_flag
	size = *size_flag
	
	runtime.GOMAXPROCS(size)
	
	m = martini.New()
	m.Use(martini.Recovery())
	m.Use(martini.Logger())
	// m.Use(auth.Basic(AuthUser, AuthPasswd))
	
	r := martini.NewRouter()
	r.Get(`/hello`, index)
	
	m.Action(r.Handle)
}


func main() {
	addr := fmt.Sprintf(":%d", port)
	log.Println("Listening on >> ", addr)
	// log.Fatal(http.ListenAndServeTLS(addr, "cert.pem", "key.pem", m))
	log.Fatal(http.ListenAndServe(addr, m))
}
