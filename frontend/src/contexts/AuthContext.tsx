/* eslint-disable react-refresh/only-export-components -- context exports provider + hook */
import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../supabaseClient'

export interface AuthResult {
  success: boolean
  error?: string
}

export interface AuthContextType {
  session: Session | null
  loading: boolean
  login: (email: string, password: string) => Promise<AuthResult>
  signup: (email: string, password: string) => Promise<AuthResult>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, authenticatedSession) => {
      setSession(authenticatedSession)
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    if (error) {
      return { success: false, error: error.message }
    }
    setSession(data.session)
    return { success: true }
  }, [])

  const signup = useCallback(async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signUp({ email, password })
    if (error) {
      return { success: false, error: error.message }
    }
    setSession(data.session)
    return { success: true }
  }, [])

  const logout = useCallback(async () => {
    await supabase.auth.signOut()
  }, [])

  return (
    <AuthContext.Provider
      value={{ session, loading, login, signup, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}
